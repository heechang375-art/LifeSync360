#!/bin/bash
set -e

PACKAGE_DIR="package"
ZIP_NAME="onprem_customer_query.zip"

rm -rf $PACKAGE_DIR $ZIP_NAME
mkdir $PACKAGE_DIR

cp handler.py $PACKAGE_DIR/

cd $PACKAGE_DIR
zip -r ../$ZIP_NAME . --quiet
cd ..

echo "빌드 완료: $ZIP_NAME"
echo "S3 업로드 예시:"
echo "  aws s3 cp $ZIP_NAME s3://<bucket>/lambda/onprem_customer_query/$ZIP_NAME"
