#!/bin/bash

###############################################################################
# LOAD ENV
###############################################################################

source ./config/db.env

###############################################################################
# LOG
###############################################################################

LOG_DIR=./logs
mkdir -p $LOG_DIR

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

LOG_FILE=$LOG_DIR/lifesync360_verify_$TIMESTAMP.log

###############################################################################
# DEFAULT
###############################################################################

AWS_REGION=${AWS_REGION:-ap-northeast-3}
DB_NAME=${DB_NAME:-lifesync360}
DB_PORT=${DB_PORT:-3306}
DB_CHARSET=${DB_CHARSET:-utf8mb4}

###############################################################################
# GET CLUSTER
###############################################################################

if [ -z "$AURORA_CLUSTER_ID" ]; then

    export AURORA_CLUSTER_ID=$(aws rds describe-db-clusters \
        --region ${AWS_REGION} \
        --query "DBClusters[0].DBClusterIdentifier" \
        --output text)

fi

###############################################################################
# GET HOST
###############################################################################

if [ -z "$DB_HOST" ]; then

    export DB_HOST=$(aws rds describe-db-clusters \
        --region ${AWS_REGION} \
        --db-cluster-identifier ${AURORA_CLUSTER_ID} \
        --query "DBClusters[0].Endpoint" \
        --output text)

fi

###############################################################################
# GET USER
###############################################################################

if [ -z "$DB_USER" ]; then

    export DB_USER=$(aws rds describe-db-clusters \
        --region ${AWS_REGION} \
        --db-cluster-identifier ${AURORA_CLUSTER_ID} \
        --query "DBClusters[0].MasterUsername" \
        --output text)

fi

###############################################################################
# GET SECRET
###############################################################################

if [ -z "$SECRET_ARN" ]; then

    export SECRET_ARN=$(aws rds describe-db-clusters \
        --region ${AWS_REGION} \
        --db-cluster-identifier ${AURORA_CLUSTER_ID} \
        --query "DBClusters[0].MasterUserSecret.SecretArn" \
        --output text)

fi

###############################################################################
# GET PASSWORD
###############################################################################

if [ -z "$DB_PASSWORD" ]; then

    export DB_PASSWORD=$(aws secretsmanager get-secret-value \
        --secret-id ${SECRET_ARN} \
        --region ${AWS_REGION} \
        --query SecretString \
        --output text | jq -r '.password')

fi

###############################################################################
# MYSQL ENV
###############################################################################

export MYSQL_PWD="${DB_PASSWORD}"

###############################################################################
# MYSQL CMD
###############################################################################

MYSQL_CMD="mysql \
-h${DB_HOST} \
-P${DB_PORT} \
-u${DB_USER} \
--default-character-set=${DB_CHARSET} \
${DB_NAME}"

###############################################################################
# START
###############################################################################

echo ""
echo "###############################################################################"
echo "LifeSync360 DATA VERIFY START"
echo "###############################################################################"

###############################################################################
# FUNCTION
###############################################################################

verify_table() {

    TABLE_NAME=$1

    echo ""
    echo "###############################################################################" | tee -a ${LOG_FILE}
    echo "VERIFY TABLE : ${TABLE_NAME}" | tee -a ${LOG_FILE}
    echo "###############################################################################" | tee -a ${LOG_FILE}

    ${MYSQL_CMD} -e "
    USE ${DB_NAME};

    SELECT COUNT(*) AS total_count
    FROM ${TABLE_NAME};

    SELECT *
    FROM ${TABLE_NAME}
    LIMIT 10;
    " 2>&1 | tee -a ${LOG_FILE}

}

###############################################################################
# VERIFY
###############################################################################

verify_table "company_master"

verify_table "category_master"

verify_table "product_master"

verify_table "product_option"

verify_table "recommend_rule"

verify_table "cross_sell_rule"

verify_table "campaign_master"

###############################################################################
# RECOMMENDATION TEST
###############################################################################

echo ""
echo "###############################################################################" | tee -a ${LOG_FILE}
echo "VIP RECOMMENDATION TEST" | tee -a ${LOG_FILE}
echo "###############################################################################" | tee -a ${LOG_FILE}

${MYSQL_CMD} -e "

USE ${DB_NAME};

SELECT
    c.company_name,
    p.product_name,
    rr.target_grade,
    rr.priority_rank

FROM recommend_rule rr

JOIN category_master cat
    ON rr.category_code = cat.category_code

JOIN product_master p
    ON p.category_id = cat.category_id

JOIN company_master c
    ON p.company_id = c.company_id

WHERE rr.target_grade='VIP'
  AND 92.4 BETWEEN rr.min_score
               AND rr.max_score

ORDER BY rr.priority_rank ASC,
         p.priority_rank ASC

LIMIT 20;

" 2>&1 | tee -a ${LOG_FILE}

###############################################################################
# COMPLETE
###############################################################################

echo ""
echo "###############################################################################"
echo "LifeSync360 DATA VERIFY COMPLETE"
echo "LOG FILE : ${LOG_FILE}"
echo "###############################################################################"