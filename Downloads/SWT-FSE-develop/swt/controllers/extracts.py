from ._controller import ModelControllerFactory as _controller
from flask import g, request
from swt.exceptions.api_expections import ApiSqlException, ApiUnauthorizedOperationException, ApiException
import json
import xlwt
import boto.ses
from scripts.s3 import S3
import requests
from tempfile import SpooledTemporaryFile
import zipfile
from uuid import uuid4


class Extracts(_controller):
    def __init__(self, *args):
        super(Extracts, self).__init__(*args)

    def zip_multi_seq(self, _files):
        bucket = self._config.get("aws", "s3_bucket")
        sequence_zip_filefolder = self._config.get("aws", "s3_sequence_zip_filefolder")
        aws_configuration = {
            'aws_access_key_id': self._config.get('aws', 'aws_access_key_id'),
            'aws_secret_access_key': self._config.get('aws', 'aws_secret_access_key'),
            'region_name': self._config.get('aws', 'aws_region')
        }

        _s3 = S3(credentials=aws_configuration, logger=self._logger)

        with SpooledTemporaryFile() as fh:
            with zipfile.ZipFile(fh, 'w') as myzip:
                for url in _files:
                    url = url.strip()
                    fname = url.split("/")[-1]
                    req = requests.get(url)
                    if req.status_code < 400:
                        res = req.text
                        myzip.writestr(fname, res, )
            fh.seek(0)
            key = "{}/{}.zip".format(sequence_zip_filefolder, str(uuid4()))

            pre_signed_url = _s3.upload(bucket, key, fh)

        return pre_signed_url

    def get_sequence_url_of_extract(self, extracts, cursor, db_name):

        incomplete = "+".join([extract["extract_id"] for extract in extracts if extract["status"] != "Completed"])

        if not incomplete:
            return False

        query = "{}/solr/consensus_sequence/select?q=*%3A*&fq=extract_identifier%3A({})&fl=file_name%2C+extract_identifier%2C+sample_identifier%2C+sample_id&wt=json".format(
            self._config.get("solr", "url"), incomplete)

        r = requests.get(query)

        if r.status_code < 400:
            resp = r.json()
            n_res = int(resp.get("response", {}).get("numFound", 0))
            seqs = resp.get("response", {}).get("docs", [])
            for seq in seqs:
                _files = seq.get("file_name").split(",")
                if len(_files) > 1:
                    url = self.zip_multi_seq(_files)
                else:
                    url = _files[0]

                url = url[5:] if url.startswith("s3://") else url

                query = """UPDATE `{}`.`Extracts` SET `status`="Completed", `results`="{}" WHERE `extract_id` LIKE "{}";
                                        """.format(db_name, url, seq.get("extract_identifier"))
                try:
                    res = cursor.execute(query)
                except Exception as e:
                    raise ApiSqlException(description=e)
                else:
                    pass

                    # TODO: log is not res

            return n_res
        return False

    def _get_extracts(self, user, cursor):

        db_name = self._config.get("MySql", "db")
        core_admin = user.get("digs")

        extracts = []
        requestNumbers = set()
        requesters_ = set()

        base_query = """SELECT
                          Extracts.id,
                          Requests.requester,
                          Requests.digs_id,
                          Requests.institution,
                          Extracts.extract_id,
                          Digs_.digs_core_number AS digs,
                          Extracts.results,
                          Extracts.status
                        FROM {}.Extracts AS Extracts
                        JOIN {}.Requests AS Requests
                          ON Extracts.request_id = Requests.id
                        JOIN {}.Digs AS Digs_
                          ON Requests.digs_id = Digs_.id
                        WHERE
        """.format(db_name, db_name, db_name, db_name)

        if core_admin:
            where_query = """{}.Requests.digs_id IN (SELECT
                          id
                        FROM {}.Digs as Digs_
                        WHERE digs_core_number IN (\"{}\"))""". \
                format(db_name, db_name, "\",\"".join(core_admin.keys()))
        else:
            where_query = """ Requests.requester LIKE \"{}\"""".format(user.get("ldap", {}).get("actor_username"))

        try:
            cursor.execute(base_query + where_query)
        except Exception as e:
            print(e)
            raise ApiSqlException(description=e)
        else:
            columns = [field[0] for field in cursor.description]
            for row in cursor:
                r = {k: v for k, v in zip(columns, row)}
                extracts.append(r)
                requesters_.add(r.get("requester"))
                try:
                    requestNumbers.add(int(r.get("extract_id").split("_")[0][1:]))
                except:
                    pass
        return extracts, requesters_, requestNumbers

    def get_extracts(self, user):
        conn = g._db
        db_name = self._config.get("MySql", "db")
        core_admin = user.get("digs")

        resp = {"status": True, "core": bool(core_admin), "requesters": [], "requestNumbers": [], "extracts": [],
                "digs": core_admin}
        requesters_dict = {}
        requesters = []

        with conn.cursor() as cursor:

            extracts, requesters_, requestNumbers = self._get_extracts(user, cursor)

            update_sequencing_results = self.get_sequence_url_of_extract(extracts, cursor, db_name)
            conn.commit()
            if update_sequencing_results:
                extracts, requesters_, requestNumbers = self._get_extracts(user, cursor)

            for requester in requesters_:
                user = self.user.get_user(requester, swt=False, ldap=True)  # TODO: cache this
                first_last_name = "{} {}".format(user.get("ldap", {}).get("actor_first_name", requester),
                                                 user.get("ldap", {}).get("actor_last_name", requester))
                requesters_dict[requester] = first_last_name
                requesters.append(first_last_name)
            resp["requesters"] = {requester_n: False for requester_n in list(requesters)}
            resp["requestNumbers"] = list(map(lambda x: ("R" + str(x)), sorted(requestNumbers)))

            for extract in extracts:
                extract["requester"] = requesters_dict[extract["requester"]]
            resp["extracts"] = extracts

        return resp

    def insert_extracts(self, user, payload):
        """Insert multiple extracts into the database, as a single request

        :param user:
        :param payload:
        :return:
        """
        conn = g._db
        db_name = self._config.get("MySql", "db")
        env = self._config.get("api", "env")
        cor_admin = user.get("digs")

        # self._logger.error("oopies")

        user_info = payload.get("user")
        samples = payload.get("samples")
        facility = payload.get("facility")
        manifesto = payload.get("manifesto")
        institution = user.get("ldap", {}).get("actor_institution")
        request_uid = str(uuid4())

        fse_choices = facility.get("digs")
        fse = []
        for key in fse_choices:
            try:
                rank = int(key)
            except:
                pass
            else:
                fse.append(fse_choices[str(rank)])

        request_id = None
        emailed = None

        # Create request
        query = """INSERT INTO `{}`.`Requests` (`uid`, `digs_id`, `fse`, `requester`, `institution`, `created` )
                  VALUES (\"{}\", (SELECT id from `{}`.`Digs` WHERE digs_core_number LIKE \"{}\"), \'{}\', "{}", \"{}\", NOW())""" \
            .format(db_name, request_uid, db_name, facility.get("choice"), json.dumps(fse),
                    user.get("ldap", {}).get("actor_username"), institution)

        with conn.cursor() as cursor:
            try:
                cursor.execute(query)
                conn.commit()
            except Exception as e:
                raise ApiSqlException(code=500, description=str(e))
            else:
                query = """SELECT id from `{}`.`Requests` WHERE `uid` LIKE '{}'""".format(db_name, request_uid)
                try:
                    cursor.execute(query)
                    columns = [field[0] for field in cursor.description]
                    res = cursor.fetchone()
                    if res:
                        request = dict(zip(columns, [res[0]]))
                except Exception as e:
                    self._logger.error(e, query)
                    raise ApiSqlException(code=500, description=str(e))
                else:
                    request_id = request.get("id")
            if request_id:
                wb = xlwt.Workbook()
                ws = wb.add_sheet('sequencing request')
                ws.write(0, 0, "Requester:")
                ws.write(1, 0, user_info.get("name"))
                ws.write(2, 0, user_info.get("institution"))
                ws.write(3, 0, user_info.get("street_address"))
                ws.write(4, 0, "{} {} {}".format(user_info.get("city"), user_info.get("state_province"),
                                                 user_info.get("zipcode")))
                ws.write(5, 0, user_info.get("country"))
                ws.write(6, 0, user_info.get("daytime_phone"))
                ws.write(7, 0, user_info.get("email"))
                ws.write(9, 0, "Extracts:")
                ws.write(11, 0, "Sample Identifier")
                ws.write(11, 1, "Project Identifier")
                ws.write(11, 2, "Submission Type")
                ws.write(11, 3, "Submission ID")
                ws.write(11, 4, "Extract Identifier")
                ws.write(11, 5, "Extract Material")
                ws.write(11, 6, "Analysis Type")

                for row, sample in enumerate(samples, 12):
                    extract_id = "R{}_{}".format(request_id, sample["extract_id"])
                    query = """INSERT INTO `{}`.`Extracts` (`request_id`, `sample_id`, `extract_id`,
                                    `sequencing_study_identifier`, `submission_id`, `submission_type`, `submitter_name`,
                                    `submission_date`, `project_identifier`, `virus_identifier`, `influenza_subtype`,
                                    `host_species`, `lab_host`, `passage_history`, `pathogenicity`, `extract_material`,
                                    `volume`, `concentration`, `concentration_determined_by`, `sequencing_tecnhology`,
                                     `analysis_type`, `raw_sequences`, `comments`, `status`, `created`, `sample_identifier`)
                                VALUES( {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}',
                                    '{}', '{}', {}, {}, '{}', '{}', '{}','{}', '{}', 'Requested', CURRENT_TIMESTAMP, '{}' )""". \
                        format(db_name, request_id, sample.get("sample_id"), extract_id,
                               sample.get("sequencing_study_identifier"),
                               sample.get("submission_id"), sample.get("submission_type"), sample.get("submitter_name"),
                               sample.get("submission_date"), sample.get("project_identifier"),
                               sample.get("virus_identifier"),
                               sample.get("influenza_subtype"), sample.get("host_species"), sample.get("lab_host"),
                               sample.get("passage_history"), sample.get("pathogenicity"),
                               sample.get("extract_material"),
                               sample.get("volume"), sample.get("concentration"),
                               sample.get("concentration_determined_by"),
                               json.dumps(sample.get("sequencing_technology")), json.dumps(sample.get("analysis_type")),
                               sample.get("raw_sequences"), sample.get("comments"), sample.get("sample_identifier"))
                    try:
                        res = cursor.execute(query)
                        if res:
                            conn.commit()
                    except Exception as e:
                        self._logger.error(e, query)
                        # TODO: log error / raise sql exception (log all exceptions)
                        raise ApiSqlException(code=500, description="failed to save extracts")
                    else:
                        analysis_type = " / ".join(
                            [analysis for analysis in sample["analysis_type"] if sample["analysis_type"][analysis]])
                        ws.write(row, 0, sample.get("sample_id"))
                        ws.write(row, 1, sample.get("project_identifier"))
                        ws.write(row, 2, sample.get("submission_type"))
                        ws.write(row, 3, sample.get("submission_id", 0))
                        ws.write(row, 4, extract_id)
                        ws.write(row, 5, sample.get("extract_material"))
                        ws.write(row, 6, analysis_type)

                wb.save("manifest.xls")
                with SpooledTemporaryFile() as fh:
                    wb.save(fh)
                    fh.seek(0)
                    aws_configuration = {
                        'aws_access_key_id': self._config.get('aws', 'aws_access_key_id'),
                        'aws_secret_access_key': self._config.get('aws', 'aws_secret_access_key'),
                        'region_name': self._config.get('aws', 'aws_region')
                    }

                    _s3 = S3(credentials=aws_configuration, logger=self._logger)

                    filename = "request_{}.{}".format(request_id, "xls")
                    bucket = self._config.get("aws", "s3_bucket")
                    # bucket = "swt-prod"
                    key = "manifest-files/" + filename

                    pre_signed_url = _s3.upload(bucket, key, fh)

                    if not pre_signed_url:
                        return {"status": False,
                                "statusText": "Error uploading manifest to aws"}

                    conn = boto.ses.connect_to_region(**aws_configuration)
                    email_from = 'support@niaidceirs.org'
                    email_subject = 'New Sequencing Request'
                    email_body = """<p>You've received a new Sequencing request with id R{} You can find the request
                                  <a href = '{}'>here</a>. Please see more information about
                                  this sequencing request in the swt app.</p>""".format(request_id, pre_signed_url)

                    if env == "prod":
                        email_to = facility.get("digs", {}).get("contact_email", {}).get(facility.get("choice"))
                    else:
                        email_to = user_info.get("email")

                    emailed = conn.send_email(email_from, email_subject, None, to_addresses=email_to, format="html",
                                              html_body=email_body)

                    if not emailed:
                        raise ApiException(code=500, title=False,
                                           description="Extracts have been saved, but there was a problem emailing the DIGS facility. Please contact the DPCC")
                    return {"status": True, "request_id": request_id}

    def update_extract(self, user):
        """ Generic update of any extract field

        :param user:
        :return:
        """
        pass

    def update_status(self, user, payload=None):
        """payload comes comes in as Multidict, wich converts nicely to dict, except lists are serialized funny:
        {'extract_row_id': ['12'], 'name': ['status'], 'value': ['Requested'], 'extracts_to_update_status[0]': ['6'], 'extracts_to_update_status[1]': ['12'], 'extracts_to_update_status[2]': ['13'], 'extracts_to_update_status[3]': ['14']}

        payload must be parsed for items that are of type list

        :param user:
        :param payload:
        :return:
        """
        payload_temp = {}
        for key in payload:
            if "[" in key:
                k = key.split("[")[0]
                if k not in payload_temp:
                    payload_temp[k] = [payload[key][0]]
                else:
                    payload_temp[k].append(payload[key][0])
            else:
                payload_temp[key] = payload[key][0]

        payload = payload_temp
        id_ = int(payload.get("extract_row_id"))

        cor_admin = user.get("digs")
        if not cor_admin:
            self._logger.warning("Non-admin user cannot modify request status: {}".format(user))
            raise ApiUnauthorizedOperationException(code=412, description="Non-admin user cannot modify request status")

        conn = g._db
        db_name = self._config.get("MySql", "db")

        with conn.cursor() as cursor:
            if id_:
                query = """SELECT Digs.digs_core_number FROM `{}`.`Requests` Requests
                    JOIN `{}`.`Digs` as Digs
                    ON Digs.id = digs_id
                    WHERE Requests.`id` LIKE
                    (SELECT request_id FROM `{}`.`Extracts` WHERE id LIKE {})
                """.format(db_name, db_name, db_name, id_)

                try:
                    cursor.execute(query)
                except Exception:
                    raise ApiSqlException()
                else:
                    columns = [field[0] for field in cursor.description]
                    res = cursor.fetchone()
                    if res:
                        extracts_digs = dict(zip(columns, [res[0]]))

                        if extracts_digs["digs_core_number"] not in user.get("digs").keys():
                            raise ApiUnauthorizedOperationException(
                                description="Cannot modify extract without admin role for facility sequencing this extract")

                        # TODO: validate that the digs for each and every extracts is authorized for the user, not only the one in the id
                        extracts_to_update_status = list(
                            set(map(lambda x: str(x), payload.get("extracts_to_update_status"))))

                        query = """
                              UPDATE `{}`.`Extracts` SET `status`="{}" WHERE `id` in ({});
                        """.format(db_name, payload.get("value"), ",".join(extracts_to_update_status))
                        try:
                            cursor.execute(query)
                            conn.commit()
                        except Exception:
                            raise ApiSqlException()
                        else:
                            return True
