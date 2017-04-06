from swt.exceptions.api_expections import ApiPreconditionFailedException, ApiSqlException
from ._controller import ModelControllerFactory as _controller
from flask import g
from swt.scripts import usps_shipping


class FSE(_controller):
    """Rank possible digs facilities that can handle the requested sequencing job

    """
    def __init__(self, *args):
        super(FSE, self).__init__(*args)

    def get_possible_digs(self, cursor, db_name, sequencing_tech):
        """ Get active digs facilities, their capacity, and initialize the response dictionary with the
        active digs facilities

        Args:
         sequencing_tech (list): sequencing technology requested for the sequencing job

        Returns:
             tuple: (list, dict, dict, list)
        """

        cursor.execute("""SELECT * FROM `{}`.`Digs_Capacity` WHERE `active` LIKE 1""".format(db_name))
        columns = [field[0] for field in cursor.description]
        digs_capacity = []
        for row in cursor:
            column_value = (list(zip(columns, row)))
            v = [{k: v for k, v in column_value}][0]
            digs_capacity.append(v)

        possible_digs = [dig for dig in digs_capacity if
                         any(list(map(lambda instrument: instrument in dig.get("instruments_operational"), sequencing_tech)))]

        if not possible_digs:
            return None, None, None, None

        possible_digs_capacity = [{'digs_id': v['digs_id'], 'capacity_total': v['capacity_total']}
                                  for v in possible_digs]

        full_list = ["DIGS-" + str(digs.get("digs_id")) for digs in digs_capacity]
        response = {str(digs.get("digs_id")): None for digs in digs_capacity}
        response["0"] = None  # 0 hold non-available digs to the user request

        all_ids = [dig['digs_id'] for dig in digs_capacity]

        return possible_digs, possible_digs_capacity, response, all_ids, full_list

    def digs_current_usage(self, cursor, db_name):
        """ Get the current available capacity of each digs facility

        Args:
            cursor (pymysql.cursors.Cursor): The cursor to execute the query
            db_name (str): the database name

        Returns:
            list: [{'current_requests': <int>, 'digs_id': <int>}]
        """

        query = """SELECT
                   COUNT(*) as current_requests, r.digs_id
                   FROM {}.Extracts as e JOIN {}.Requests as r
                   on e.request_id=r.id
                   WHERE e.status NOT IN ("complete", "Complete", "Failed-Samples Not Received",
                                          "Failed-Sample QC", "Failed-Sequencing/Assembly")
                   GROUP BY r.digs_id """.format(db_name, db_name)
        try:
            cursor.execute(query)
        except Exception as e:
            self._logger.error(e, exc_info=True)
            raise ApiSqlException(description="Failed to select sequecing facility")

        columns = [field[0] for field in cursor.description]
        digs_requests = []
        for row in cursor:
            column_value = (list(zip(columns, row)))
            digs_requests.append([{k: v for k, v in column_value}][0])
        return digs_requests

    def get_candidate_facilities(self, digs_requests, possible_digs_capacity, number_extracts):
        """ Get list of candidate facilities with enough capacity to handle the job and sequencing tech requested

        Args:
            digs_requests (list): [{'current_requests': <int>, 'digs_id': <int>}]
            possible_digs_capacity (list): [{'digs_id': <int>, 'capacity_total': <int>}]
            number_extracts (int): The number of sequencing extracts being requested

        Returns:
            list: list of ids of candidate facilities

        """

        for v in digs_requests:
            for w in possible_digs_capacity:
                if w['digs_id'] == v['digs_id']:
                    w['current_capacity'] = w['capacity_total'] - v['current_requests']
                else:
                    w['current_capacity'] = w['capacity_total']
        candidates = [v for v in possible_digs_capacity if v['current_capacity'] >= number_extracts]
        candidates_id = [v['digs_id'] for v in candidates]
        return candidates_id

    def get_digs_info(self, cursor, db_name):
        """ Get relavant information for the digs facilities
        Args:
            cursor (pymysql.cursors.Cursor): The cursor to execute the query
            db_name (str): the database name

        Returns:
            dict: id, digs_core_number, contact_email, shipping_adddress_zip for each digs id
        """
        query = """SELECT id, digs_core_number, contact_email, shipping_adddress_zip
                    FROM `{}`.`Digs`
                   """ \
            .format(db_name)

        cursor.execute(query)

        columns = [field[0] for field in cursor.description]
        digs_info_ = []
        digs_info = {}
        for row in cursor:
            column_value = (list(zip(columns, row)))
            digs_info_.append(column_value)

        for digs in digs_info_:
            d = dict(digs)
            digs_info[d.get("id")] = d

        return digs_info

    def get_shipping_cost_to_each_facility(self, digs_info, candidates_id, zipcode):
        """calculate shipping cost to each available facility

        Args:
            digs_info (dict): relevant fields of each digs
            candidates_id (list):  list of possible digs for the job
            zipcode (str | int): user's origin zipcode

        Returns:
            dict: {<id>: <cost>}
        """
        cost = {}
        for _id in candidates_id:
            destzip = digs_info[_id].get("shipping_adddress_zip").split("-")[0]

            try:
                rate = usps_shipping(zipcode, destzip)
            except Exception:
                raise ApiPreconditionFailedException(
                    description="can't calculate shipping rate. Check that the zipcode is valid")
            else:
                cost[_id] = rate
        return cost

    def get_response(self, candidates_id, cursor, response,possible_digs_capacity, all_ids, full_list, db_name, zipcode):
        """ Build the response object

        Args:
            candidates_id (list): list of candidate facility ids (a subset of all the ids)
            cursor (pymysql.cursors.Cursor): The cursor to execute the query
            response (dict): the initialized response object
            possible_digs_capacity:
            all_ids (list): list of the ids of all facilities
            full_list (list): list of DIGS-<ID>   ['DIGS-1', 'DIGS-2', 'DIGS-3', 'DIGS-4', 'DIGS-5', 'DIGS-6']
            db_name (str): the database name
            zipcode (str | int): origin zipcode

        Returns:
            dict: the response object
        """

        if len(candidates_id) == 0:
            response["0"] = full_list
            response["1"] = []
            response_c = response.copy()
            response = {key: response_c[key] for key in response_c if response_c[key] is not None}
        elif len(candidates_id) == 1:
            response["0"] = full_list
            response["1"] = "DIGS-" + str(candidates_id[0])
            response_c = response.copy()
            response = {key: response_c[key] for key in response_c if response_c[key] is not None}
        else:
            digs_info = self.get_digs_info(cursor, db_name)
            cost = self.get_shipping_cost_to_each_facility(digs_info, candidates_id, zipcode)
            # cost is a dict: {id: shipping_rate}
            if not any(cost.values()):
                # TODO: Kailin: use alternative to shipping cost
                unavailable_digs_ids = list(set(all_ids) - set(cost))
                unavailable_digs = ["DIGS-" + str(i) for i in unavailable_digs_ids]
                response["0"] = unavailable_digs
                sorted_cap = sorted(possible_digs_capacity, key=lambda k: k['current_capacity'], reverse = True)
                for i, cap in enumerate(sort_cap):
                    response[str(i + 1)] = "DIGS-" + str(cap['digs_id'])
        
            else:
                sort_c = sorted(cost, key=cost.__getitem__)
                unavailable_digs_ids = list(set(all_ids) - set(sort_c))
                unavailable_digs = ["DIGS-" + str(i) for i in unavailable_digs_ids]
                response["0"] = unavailable_digs
                sort_c += ['None'] * (len(full_list) - len(cost))

                for i, cost in enumerate(sort_c):
                    response[str(i + 1)] = "DIGS-" + str(cost)

                response = {key: response[key] for key in response if response[key] != "DIGS-None"}

        response["contact_email"] = {digs_info[contact].get("digs_core_number"): digs_info[contact].get("contact_email") for contact in digs_info}

        return response

    def select_facility(self, zipcode, number_extracts, sequencing_tech):
        """Get ranked digs facilities for the sequencing job

        Args:
            zipcode (str|int): the origin zipcode
            number_extracts (int): the number of extracts being sequenced
            sequencing_tech (list): list of sequencing technologies requested

        Returns:
            dict: the response object

        Raises:
            ApiPreconditionFailedException

        """

        conn = g._db
        db_name = self._config.get("MySql", "db")

        response = None
        with conn.cursor() as cursor:
            try:
                possible_digs, possible_digs_capacity, response, all_ids, full_list = self.get_possible_digs(cursor, db_name, sequencing_tech)
            except Exception as e:
                self._logger.error(e, exc_info=True)
                raise ApiPreconditionFailedException(description="Facility Selection failed")

            if not possible_digs:
                raise ApiPreconditionFailedException(description="No facility available with sequencing capacity for the requested instruments")

            try:
                digs_requests = self.digs_current_usage(cursor, db_name)
                with_requests = [int(x["digs_id"]) for x in digs_requests]
                digs_requests += [{'current_requests': 0, 'digs_id': x} for x in all_ids if x not in with_requests]
                candidates_id = self.get_candidate_facilities(digs_requests, possible_digs_capacity, number_extracts)
                response = self.get_response(candidates_id, cursor, response, all_ids, full_list, db_name, zipcode)
            except ApiPreconditionFailedException as e:
                self._logger.error(e, exc_info=True)
                raise ApiPreconditionFailedException(description=e.description)
            except Exception as e:
                self._logger.error(e, exc_info=True)
                raise ApiPreconditionFailedException(description="Facility Selection failed")

        if not response:
            raise ApiPreconditionFailedException(description="Facility Selection failed")
        return response

    @staticmethod
    def validate_zipcode(destzip, origin_zipcode=11215):
        """Validate a zipcode.

        Args:
            destzip (str | int):  the destination zipcode
            origin_zipcode (str | int):  the origin zipcode:

        Returns:
            Bool: True if shipping rate can be calculated

        Raises:
            ApiPreconditionFailedException if zipcode is invalid format or non-existent
        """

        try:
            usps_shipping(origin_zipcode, destzip)
        except Exception:
            """Only raises exception if usps returns an error in the xml. If it can't communicate, returns None
            """
            raise ApiPreconditionFailedException(description="can't calculate the shipping rate. Check that the zipcode is valid")
        return True
