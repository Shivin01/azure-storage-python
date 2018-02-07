# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import unittest

from azure.common import AzureHttpError

from azure.storage.blob import BlockBlobService
from azure.storage.common import (
    Logging,
    Metrics,
    CorsRule,
    RetentionPolicy,
    DeleteRetentionPolicy,
)
from azure.storage.file import FileService
from azure.storage.queue import QueueService
from tests.testcase import (
    StorageTestCase,
    record,
    not_for_emulator,
)


# ------------------------------------------------------------------------------


class ServicePropertiesTest(StorageTestCase):
    def setUp(self):
        super(ServicePropertiesTest, self).setUp()

        self.bs = self._create_storage_service(BlockBlobService, self.settings)
        self.qs = self._create_storage_service(QueueService, self.settings)

        # file service is not supported on the emulator
        if not self.settings.IS_EMULATED:
            self.fs = self._create_storage_service(FileService, self.settings)

    # --Helpers-----------------------------------------------------------------
    def _assert_properties_default(self, prop):
        self.assertIsNotNone(prop)

        self._assert_logging_equal(prop.logging, Logging())
        self._assert_metrics_equal(prop.hour_metrics, Metrics())
        self._assert_metrics_equal(prop.minute_metrics, Metrics())
        self._assert_cors_equal(prop.cors, list())

    def _assert_logging_equal(self, log1, log2):
        if log1 is None or log2 is None:
            self.assertEqual(log1, log2)
            return

        self.assertEqual(log1.version, log2.version)
        self.assertEqual(log1.read, log2.read)
        self.assertEqual(log1.write, log2.write)
        self.assertEqual(log1.delete, log2.delete)
        self._assert_retention_equal(log1.retention_policy, log2.retention_policy)

    def _assert_delete_retention_policy_equal(self, policy1, policy2):
        if policy1 is None or policy2 is None:
            self.assertEqual(policy1, policy2)
            return

        self.assertEqual(policy1.enabled, policy2.enabled)
        self.assertEqual(policy1.days, policy2.days)

    def _assert_delete_retention_policy_not_equal(self, policy1, policy2):
        if policy1 is None or policy2 is None:
            self.assertNotEqual(policy1, policy2)
            return

        self.assertFalse(policy1.enabled == policy2.enabled
                         and policy1.days == policy2.days)

    def _assert_metrics_equal(self, metrics1, metrics2):
        if metrics1 is None or metrics2 is None:
            self.assertEqual(metrics1, metrics2)
            return

        self.assertEqual(metrics1.version, metrics2.version)
        self.assertEqual(metrics1.enabled, metrics2.enabled)
        self.assertEqual(metrics1.include_apis, metrics2.include_apis)
        self._assert_retention_equal(metrics1.retention_policy, metrics2.retention_policy)

    def _assert_cors_equal(self, cors1, cors2):
        if cors1 is None or cors2 is None:
            self.assertEqual(cors1, cors2)
            return

        self.assertEqual(len(cors1), len(cors2))

        for i in range(0, len(cors1)):
            rule1 = cors1[i]
            rule2 = cors2[i]
            self.assertEqual(len(rule1.allowed_origins), len(rule2.allowed_origins))
            self.assertEqual(len(rule1.allowed_methods), len(rule2.allowed_methods))
            self.assertEqual(rule1.max_age_in_seconds, rule2.max_age_in_seconds)
            self.assertEqual(len(rule1.exposed_headers), len(rule2.exposed_headers))
            self.assertEqual(len(rule1.allowed_headers), len(rule2.allowed_headers))

    def _assert_retention_equal(self, ret1, ret2):
        self.assertEqual(ret1.enabled, ret2.enabled)
        self.assertEqual(ret1.days, ret2.days)

    # --Test cases per service ---------------------------------------

    @record
    def test_blob_service_properties(self):
        # Arrange

        # Act
        resp = self.bs.set_blob_service_properties(logging=Logging(), hour_metrics=Metrics(),
                                                   minute_metrics=Metrics(), cors=list(), target_version='2014-02-14')

        # Assert
        self.assertIsNone(resp)
        props = self.bs.get_blob_service_properties()
        self._assert_properties_default(props)
        self.assertEqual('2014-02-14', props.target_version)

    @record
    def test_queue_service_properties(self):
        # Arrange

        # Act
        resp = self.qs.set_queue_service_properties(logging=Logging(), hour_metrics=Metrics(),
                                                    minute_metrics=Metrics(), cors=list())

        # Assert
        self.assertIsNone(resp)
        self._assert_properties_default(self.qs.get_queue_service_properties())

    @not_for_emulator
    @record
    def test_file_service_properties(self):
        # Arrange

        # Act
        resp = self.fs.set_file_service_properties(hour_metrics=Metrics(),
                                                   minute_metrics=Metrics(), cors=list())

        # Assert
        self.assertIsNone(resp)
        props = self.fs.get_file_service_properties()
        self._assert_metrics_equal(props.hour_metrics, Metrics())
        self._assert_metrics_equal(props.minute_metrics, Metrics())
        self._assert_cors_equal(props.cors, list())

    # --Test cases per feature ---------------------------------------
    @record
    def test_set_default_service_version(self):
        # Arrange

        # Act
        self.bs.set_blob_service_properties(target_version='2014-02-14')

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self.assertEqual(received_props.target_version, '2014-02-14')

    @record
    def test_set_delete_retention_policy(self):
        # Arrange
        delete_retention_policy = DeleteRetentionPolicy(enabled=True, days=2)

        # Act
        self.bs.set_blob_service_properties(delete_retention_policy=delete_retention_policy)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_delete_retention_policy_equal(received_props.delete_retention_policy, delete_retention_policy)

    @record
    def test_set_delete_retention_policy_edge_cases(self):
        # Should work with minimum settings
        delete_retention_policy = DeleteRetentionPolicy(enabled=True, days=1)
        self.bs.set_blob_service_properties(delete_retention_policy=delete_retention_policy)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_delete_retention_policy_equal(received_props.delete_retention_policy, delete_retention_policy)

        # Should work with maximum settings
        delete_retention_policy = DeleteRetentionPolicy(enabled=True, days=365)
        self.bs.set_blob_service_properties(delete_retention_policy=delete_retention_policy)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_delete_retention_policy_equal(received_props.delete_retention_policy, delete_retention_policy)

        # Should not work with 0 days
        delete_retention_policy = DeleteRetentionPolicy(enabled=True, days=0)

        with self.assertRaises(AzureHttpError):
            self.bs.set_blob_service_properties(delete_retention_policy=delete_retention_policy)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_delete_retention_policy_not_equal(received_props.delete_retention_policy, delete_retention_policy)

        # Should not work with 366 days
        delete_retention_policy = DeleteRetentionPolicy(enabled=True, days=366)

        with self.assertRaises(AzureHttpError):
            self.bs.set_blob_service_properties(delete_retention_policy=delete_retention_policy)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_delete_retention_policy_not_equal(received_props.delete_retention_policy, delete_retention_policy)

    @record
    def test_set_disabled_delete_retention_policy(self):
        # Arrange
        delete_retention_policy = DeleteRetentionPolicy(enabled=False)

        # Act
        self.bs.set_blob_service_properties(delete_retention_policy=delete_retention_policy)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_delete_retention_policy_equal(received_props.delete_retention_policy, delete_retention_policy)

    @record
    def test_set_logging(self):
        # Arrange
        logging = Logging(read=True, write=True, delete=True, retention_policy=RetentionPolicy(enabled=True, days=5))

        # Act
        self.bs.set_blob_service_properties(logging=logging)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_logging_equal(received_props.logging, logging)

    @record
    def test_set_hour_metrics(self):
        # Arrange
        hour_metrics = Metrics(enabled=True, include_apis=True, retention_policy=RetentionPolicy(enabled=True, days=5))

        # Act
        self.bs.set_blob_service_properties(hour_metrics=hour_metrics)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_metrics_equal(received_props.hour_metrics, hour_metrics)

    @record
    def test_set_minute_metrics(self):
        # Arrange
        minute_metrics = Metrics(enabled=True, include_apis=True,
                                 retention_policy=RetentionPolicy(enabled=True, days=5))

        # Act
        self.bs.set_blob_service_properties(minute_metrics=minute_metrics)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_metrics_equal(received_props.minute_metrics, minute_metrics)

    @record
    def test_set_cors(self):
        # Arrange
        cors_rule1 = CorsRule(['www.xyz.com'], ['GET'])

        allowed_origins = ['www.xyz.com', "www.ab.com", "www.bc.com"]
        allowed_methods = ['GET', 'PUT']
        max_age_in_seconds = 500
        exposed_headers = ["x-ms-meta-data*", "x-ms-meta-source*", "x-ms-meta-abc", "x-ms-meta-bcd"]
        allowed_headers = ["x-ms-meta-data*", "x-ms-meta-target*", "x-ms-meta-xyz", "x-ms-meta-foo"]
        cors_rule2 = CorsRule(allowed_origins, allowed_methods, max_age_in_seconds,
                              exposed_headers, allowed_headers)

        cors = [cors_rule1, cors_rule2]

        # Act
        self.bs.set_blob_service_properties(cors=cors)

        # Assert
        received_props = self.bs.get_blob_service_properties()
        self._assert_cors_equal(received_props.cors, cors)

    # --Test cases for errors ---------------------------------------
    @record
    def test_retention_no_days(self):
        # Assert
        self.assertRaises(ValueError,
                          RetentionPolicy,
                          True, None)

    @record
    def test_too_many_cors_rules(self):
        # Arrange
        cors = []
        for i in range(0, 6):
            cors.append(CorsRule(['www.xyz.com'], ['GET']))

        # Assert
        self.assertRaises(AzureHttpError,
                          self.bs.set_blob_service_properties,
                          None, None, None, cors)

    @record
    def test_retention_too_long(self):
        # Arrange
        minute_metrics = Metrics(enabled=True, include_apis=True,
                                 retention_policy=RetentionPolicy(enabled=True, days=366))

        # Assert
        self.assertRaises(AzureHttpError,
                          self.bs.set_blob_service_properties,
                          None, None, minute_metrics)


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
