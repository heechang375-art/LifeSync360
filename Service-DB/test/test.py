import pymysql
import json

###############################################################################
# CUSTOMER INPUT JSON
###############################################################################

customer_data = {
    "global_id": "G001",
    "update_time": "2026-04-28T04:30:00Z",
    "dynamic_score": 92.4,
    "dynamic_grade": "VIP",
    "next_best_action": "PB_CENTER",
    "vip_prob": 0.94,
    "signup_prob": 0.81,
    "rec_prob": 0.77,
    "health_score": 88.1,
    "source": "GCP_LIFESYNC360",
    "ttl": 1777777777
}

###############################################################################
# DB CONNECTION
###############################################################################

conn = pymysql.connect(
    host="lifesync360-prod-region1-service-db-auroracluster-6ppk8fdasbbb.cluster-cwjbnmskcl5q.ap-northeast-3.rds.amazonaws.com",
    user="admin",
    password="YOUR_PASSWORD",
    database="lifesync360",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor
)

###############################################################################
# CUSTOMER INFO
###############################################################################

customer_id = customer_data["global_id"]
dynamic_grade = customer_data["dynamic_grade"]
dynamic_score = customer_data["dynamic_score"]

###############################################################################
# RECOMMEND QUERY
###############################################################################

sql = """
SELECT

    cm.company_name,

    pm.product_name,

    pm.product_code,

    rr.priority_rank,

    cat.category_name

FROM recommend_rule rr

JOIN category_master cat
    ON rr.category_code = cat.category_code

JOIN product_master pm
    ON pm.category_id = cat.category_id

JOIN company_master cm
    ON pm.company_id = cm.company_id

WHERE rr.target_grade = %s

  AND %s BETWEEN rr.min_score
             AND rr.max_score

  AND rr.active_flag = 'Y'

  AND pm.active_flag = 'Y'

ORDER BY rr.priority_rank ASC,
         pm.priority_rank ASC

LIMIT 3
"""

###############################################################################
# EXECUTE
###############################################################################

with conn.cursor() as cursor:
    cursor.execute(sql, (dynamic_grade, dynamic_score))
    rows = cursor.fetchall()

###############################################################################
# RESULT BUILD
###############################################################################

recommendations = []

for row in rows:

    recommendations.append({
        "company": row["company_name"],
        "product": row["product_name"]
    })

###############################################################################
# FINAL RESPONSE
###############################################################################

result = {
    "customer": customer_id,
    "grade": dynamic_grade,
    "score": dynamic_score,
    "recommendations": recommendations
}

###############################################################################
# PRINT RESULT
###############################################################################

print(json.dumps(result, ensure_ascii=False, indent=2))

###############################################################################
# CLOSE
###############################################################################

conn.close()