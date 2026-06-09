from django.db import models


class HorrorStory(models.Model):
    """寃利앸맂 ?쒓뎅 愿대떞/?꾩떆?꾩꽕 ?먯쿇 ?곗씠?곕? ??ν븳??"""

    # source + source_ref_id 議고빀?쇰줈 JSON ?ъ쟻????以묐났 ??μ쓣 留됰뒗??
    source = models.CharField(max_length=100)
    source_ref_id = models.CharField(max_length=100)
    title = models.TextField()
    language = models.CharField(max_length=20, default="ko")
    # 吏??愿怨꾨뒗 Neo4j媛 ?대떦?섎?濡?PostgreSQL?먮뒗 ?붾㈃ ?쒖떆??臾몄옄?대쭔 ?붾떎.
    region = models.CharField(max_length=100, blank=True)
    url = models.TextField(blank=True)
    # ?먮낯 JSON?먮뒗 ?놁쑝硫?import ?④퀎?먯꽌 content ?욌?遺꾩쑝濡??앹꽦?쒕떎.
    preview = models.TextField(blank=True)
    content = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    # ?먮낯 蹂댁〈?대굹 異뷀썑 ?뺤옣 ?꾨뱶瑜??닿린 ?꾪븳 JSON ?곸뿭?대떎.
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "horror_stories"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_ref_id"],
                name="uq_horror_stories_source_ref",
            )
        ]

    def __str__(self):
        return self.title


class MythEntity(models.Model):
    """?좏솕/?꾩꽕/愿댁씠 議댁옱 ?곗씠?곕? ??ν븳??"""

    # 媛숈? ?먮낯 id?쇰룄 ?곗씠?곗뀑???щ씪吏????덉뼱 source瑜??④퍡 ??ν븳??
    source = models.CharField(
        max_length=100,
        default="ultimate_global_mythology_1000",
    )
    source_ref_id = models.CharField(max_length=100)
    name = models.TextField()
    origin = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    behavior = models.TextField(blank=True)
    weakness = models.TextField(blank=True)
    history = models.TextField(blank=True)
    signs = models.TextField(blank=True)
    # survival_rules???먮낯?먯꽌 由ъ뒪???뺥깭?대?濡?JSONField濡?蹂댁〈?쒕떎.
    survival_rules = models.JSONField(default=list, blank=True)
    source_site = models.CharField(max_length=100, blank=True)
    source_url = models.TextField(blank=True)
    # habitats泥섎읆 而щ읆?쇰줈 怨좎젙?섏? ?딆? 媛蹂 ?곗씠?곕? ??ν븳??
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "myth_entities"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_ref_id"],
                name="uq_myth_entities_source_ref",
            )
        ]

    def __str__(self):
        return self.name


class Superstition(models.Model):
    """misin.json??誘몄떊/湲덇린 臾몄옣???먮Ц 洹몃?濡???ν븳??"""

    # taboos濡?援ъ“?뷀븯吏 ?딄퀬 superstitions???⑥닚 臾몄옣?쇰줈 ??ν븳??
    source = models.CharField(max_length=100, default="misin")
    source_ref_id = models.CharField(max_length=100)
    content = models.TextField()
    # ?꾩옱??鍮꾩썙?먯?留? 異뷀썑 遺꾨쪟/吏???꾪꽣媛 ?꾩슂?섎㈃ ?ъ슜?????덈떎.
    category = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "superstitions"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_ref_id"],
                name="uq_superstitions_source_ref",
            )
        ]

    def __str__(self):
        return self.content[:50]


class DcinsidePost(models.Model):
    """DCInside 怨듯룷 寃뚯떆?먯뿉???섏쭛???몃? 寃뚯떆湲????ν븳??

    ?ъ슜?먭? 吏곸젒 ?묒꽦?섎뒗 ?대┛ 寃뚯떆??湲? post.Post媛 ?대떦?쒕떎.
    ??紐⑤뜽? ?몃? ?섏쭛 ?곗씠?곕? 遺꾨━?댁꽌 蹂닿??섍퀬, ?꾩슂?섎㈃ pgvector 寃????곸쑝濡쒕룄 ?ъ슜?쒕떎.
    """

    CATEGORY_CHOICES = [
        ("WITNESS", "목격담"),
        ("CREATION", "창작담"),
    ]

    # ?섏쭛 異쒖쿂? ?먮낯 ?앸퀎媛믪씠??
    # ??媛믪쓣 unique濡?臾띠뼱 import ?ㅽ겕由쏀듃瑜?諛섎났 ?ㅽ뻾?대룄 以묐났 ??λ릺吏 ?딄쾶 ?쒕떎.
    source = models.CharField(max_length=100, default="dcinside_gongpow")
    source_ref_id = models.CharField(max_length=100)

    # DCInside ?먮낯 title? [寃쏀뿕], [李쎌옉] 媛숈? ?쒓렇??寃쎌슦媛 留롫떎.
    # import ?④퀎?먯꽌 ?쒓렇瑜?category濡?蹂?섑븯怨? ?붾㈃??title? 蹂몃Ц ?욌?遺꾩쑝濡?留뚮뱺??
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    region = models.CharField(max_length=100, default="?쒓뎅")
    content = models.TextField()

    # ?먮낯 title ?쒓렇泥섎읆 而щ읆?쇰줈 怨좎젙?섏? ?딆쓣 蹂댁“ ?뺣낫瑜?蹂닿??쒕떎.
    # 전처리 단계에서 뽑은 키워드 목록을 JSON 배열 형태로 저장한다.
    # 별도 키워드 테이블을 만들지 않고 DBeaver에서 바로 확인하기 위한 컬럼이다.
    keywords = models.JSONField(default=list, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dcinside_posts"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_ref_id"],
                name="uq_dcinside_posts_source_ref",
            )
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.content[:30]}"
