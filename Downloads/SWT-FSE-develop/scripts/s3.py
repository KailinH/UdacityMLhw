#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os.path import exists
import sys
import boto3
from boto3 import resource as connection
import configparser

class S3(object):
    """Class to Download/upload files to/from s3
    The key and secret must be in your ~/.aws configuration files, or provided in a credentials dictionary
    """

    def __init__(self, credentials=None, logger=None):
        """
        :param credentials: dict    optional credentials file
        :param logger: object    optional logger class
        :return:
        """
        self.s3_client = boto3.client('s3')
        if not credentials:
            self.s3 = connection('s3')
            self.s3_client = boto3.client('s3')
        else:
            aws_access_key_id = credentials["aws_access_key_id"]
            aws_secret_access_key = credentials['aws_secret_access_key']
            region_name = credentials['region_name']
            self.s3 = connection('s3', aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 region_name=region_name)
            self.s3_client = boto3.client('s3', **credentials)
        self._logger = logger

    def generate_presigned_url(self, bucket, key, client_method='get_object', expires_in=31536000, content_type=None):
        params = {'Bucket': bucket, 'Key': key}
        if content_type is not None:
            params['ContentType'] = content_type
        try:
            presigned_url = self.s3_client.generate_presigned_url(client_method, Params=params, ExpiresIn=expires_in)
        except Exception as e:
            self._logger.error(e)
        else:
            if presigned_url:
                return presigned_url
            else:
                self._logger.error("Failed to obtain pre-signed_url")
                return False

    def upload(self, bucket_name, key, data):
        """Upload a file to S3.
        :param bucket_name: bucket name
        :param key: string
        :param data: file data
        :rtype bool
        :return: sucess of failure
        """
        try:
            bucket = self.s3.Bucket(bucket_name)
            bucket.put_object(Key=key, Body=data, ACL='authenticated-read')  # public-read
        except Exception as e:
            if self._logger:
                self._logger.error(e)
            else:
                print(e)
            return False
        else:
            return self.generate_presigned_url(bucket_name, key)


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')
    #from s3 import S3
    _s3  = S3(credentials = {"aws_access_key_id":"AKIAIY6Z4Z2MPVOMXBGQ", "aws_secret_access_key": "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", "region_name": "us-east-1" }) #stag
    #_s3  = S3(credentials = {"aws_access_key_id":"AKIAIXZDCPUVFRJCKSRA", "aws_secret_access_key": "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", "region_name": "us-east-1" }) #prod
    filename = sys.argv[1]
    bucket = "swt-stag"
    #bucket = "swt-prod"
    key = "manifest-files" + filename + "_stag.csv"
    path = "/opt/swt/SWT-backend/manifest/" + filename + "_stag.csv"
    try:
       with open(path, "r") as fh:
          pre_signed_url=  _s3.upload(bucket, key, fh)
          print(pre_signed_url)
    except:
       pass
