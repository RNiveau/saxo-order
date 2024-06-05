import pulumi_aws as aws

import pulumi


def ecr_repository() -> aws.ecr.Repository:
    return aws.ecr.Repository(
        "ecr-repository",
        name="k-order",
        encryption_configurations=[
            aws.ecr.RepositoryEncryptionConfigurationArgs(
                encryption_type="AES256",
                kms_key="",
            )
        ],
        image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
            scan_on_push=False,
        ),
        image_tag_mutability="MUTABLE",
    )
