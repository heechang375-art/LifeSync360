"""
upgrade_actions_engine.py — 업그레이드 액션 개인화 엔진

현재: mock user_context 기반 시뮬레이션
운영 전환 시 교체 포인트:
  get_personalized_actions()의 user_context를
  DynamoDB(스코어/활동) + Aurora(계열사/동의) + BQ 피처 실데이터로 구성하면 됨
  → app.py /api/upgrade-actions 의 TODO 블록 참고
"""

# 액션 정의 (우선순위 순)
_ALL_ACTIONS = [
    {
        'code':   'health_checkup',
        'icon':   '🏥',
        'title':  '건강검진 수검',
        'desc':   '당해 연도 건강검진 완료',
        'points': '+500P',
        'badge':  '건강점수 +7',
    },
    {
        'code':   'wearable_link',
        'icon':   '📡',
        'title':  '웨어러블 연동',
        'desc':   '기기 데이터 연결하기',
        'points': '+200P',
        'badge':  '건강점수 +5',
    },
    {
        'code':   'walking_challenge',
        'icon':   '👟',
        'title':  '걷기 챌린지 참여',
        'desc':   '매일 8,000보 × 30일',
        'points': '+5,000P',
        'badge':  '충성도 +10',
    },
    {
        'code':   'insurance_payment',
        'icon':   '💳',
        'title':  '보험 납입 6개월 유지',
        'desc':   '연속 정상납입 유지',
        'points': '+300P',
        'badge':  '충성도 +10',
    },
    {
        'code':   'affiliate_link',
        'icon':   '🔗',
        'title':  '계열사 3개 이상 연동',
        'desc':   '데이터 동의 확대',
        'points': '+150P',
        'badge':  '충성도 +18',
    },
]


def _is_applicable(code: str, ctx: dict) -> bool:
    """
    ctx 필드 → 운영 시 실데이터 매핑 대상:
      health_score       int   건강점수 0~100        ← DynamoDB health_score
      wearable_linked    bool  웨어러블 연동 여부     ← BQ wear_steps_avg_7d > 0
      checkup_this_year  bool  당해 연도 검진 완료   ← BQ hos_last_checkup_date (연도 비교)
      insurance_months   int   보험 연속납입 개월 수  ← BQ / Aurora 보험 이력
      consent_count      int   동의 계열사 수         ← Aurora consent WHERE consent_yn='Y'
      avg_steps          int   최근 7일 평균 걸음수   ← BQ wear_steps_avg_7d
    """
    if code == 'health_checkup':
        return not ctx.get('checkup_this_year', False)
    if code == 'wearable_link':
        return not ctx.get('wearable_linked', False)
    if code == 'walking_challenge':
        return ctx.get('avg_steps', 0) < 8_000
    if code == 'insurance_payment':
        return ctx.get('insurance_months', 6) < 6
    if code == 'affiliate_link':
        return ctx.get('consent_count', 3) < 3
    return True


def get_personalized_actions(user_context: dict, max_actions: int = 5) -> list:
    """
    user_context 기반으로 해당 유저에게 필요한 액션만 반환.
    리스트 순서 = 우선순위 (health_checkup 최우선).

    운영 전환 예시:
        from upgrade_actions_engine import get_personalized_actions
        ctx = {
            'health_score':      dynamo_item['health_score'],
            'wearable_linked':   float(bq_row['wear_steps_avg_7d'] or 0) > 0,
            'checkup_this_year': bq_row['hos_last_checkup_date'][:4] == str(TODAY.year),
            'insurance_months':  aurora_row['insurance_months'],
            'consent_count':     aurora_consent_count,
            'avg_steps':         int(bq_row['wear_steps_avg_7d'] or 0),
        }
        return get_personalized_actions(ctx)
    """
    return [a for a in _ALL_ACTIONS if _is_applicable(a['code'], ctx=user_context)][:max_actions]
