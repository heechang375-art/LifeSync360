#!/bin/bash
# analytics_aggregator lambda 패키징 (handler + pymysql 의존성 포함)
set -e

PACKAGE_DIR="package"
ZIP_NAME="analytics_aggregator.zip"

rm -rf $PACKAGE_DIR $ZIP_NAME
mkdir $PACKAGE_DIR

# pymysql 의존성 lambda runtime 환경에 맞춰 설치 (manylinux2014 wheel)
pip install -r requirements.txt -t $PACKAGE_DIR --platform manylinux2014_x86_64 --only-binary=:all: --upgrade

cp handler.py $PACKAGE_DIR/

cd $PACKAGE_DIR
zip -r ../$ZIP_NAME . --quiet
cd ..

echo "빌드 완료: $ZIP_NAME"
echo "S3 업로드 예시:"
echo "  aws s3 cp $ZIP_NAME s3://<bucket>/lambda/analytics_aggregator/$ZIP_NAME"
