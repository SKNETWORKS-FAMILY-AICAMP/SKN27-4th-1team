from django.test import SimpleTestCase
from unittest.mock import patch

from archive.services.graph_nodes import (
    apply_automatic_penalties,
    convert_story_to_narration,
    extract_story_from_model_response,
    generate_node,
    is_evaluation_passed,
)
from archive.services.prompt import (
    build_generation_prompt,
    build_generation_retry_prompt,
    build_revision_prompt,
    build_tts_narration_prompt,
)
from archive.services.tts import build_tts_payload, open_story_audio_stream


class ArchivePromptAndEvaluationTests(SimpleTestCase):
    def test_extract_story_from_model_response_reads_new_story_json(self):
        response = '{"new_story": "제목 한 줄\\n\\n본문 내용"}'

        story = extract_story_from_model_response(response)

        self.assertEqual(story, "제목 한 줄\n\n본문 내용")

    def test_generation_prompt_requires_community_post_style(self):
        prompt = build_generation_prompt(
            question="복도 괴담",
            keywords=["복도"],
            source_story={
                "name": "원본",
                "type": "horror_story",
                "regions": ["서울"],
                "body": "복도에서 이상한 발소리를 들었다.",
            },
            conversation_history=[],
        )

        self.assertIn("너는 괴담 작가가 아니다.", prompt)
        self.assertIn("익명 커뮤니티", prompt)
        self.assertIn("[문체 및 연출 보강 규칙]", prompt)
        self.assertIn('절대로 "\\n" 같은 이스케이프 문자를 본문에 그대로 출력하지 마라.', prompt)
        self.assertIn("마지막 문단에는 반드시 새로운 모순을 넣어라.", prompt)
        self.assertIn('"new_story"', prompt)

    def test_generation_retry_prompt_is_compact_and_keeps_output_contract(self):
        prompt = build_generation_retry_prompt(
            question="복도 괴담",
            keywords=["복도"],
            source_story={
                "name": "원본",
                "type": "horror_story",
                "regions": ["서울"],
                "body": "복도에서 이상한 발소리를 들었다.",
            },
        )

        self.assertIn("이전 응답이 비어 있었다.", prompt)
        self.assertIn("핵심 규칙:", prompt)
        self.assertIn('"new_story"', prompt)
        self.assertLess(len(prompt), 2000)

    def test_generate_node_retries_with_compact_prompt_after_empty_response(self):
        state = {
            "question": "복도 괴담",
            "keywords": ["복도"],
            "conversation_history": [],
            "source_story": {
                "name": "원본",
                "type": "horror_story",
                "regions": ["서울"],
                "body": "복도에서 이상한 발소리를 들었다.",
            },
        }

        with patch(
            "archive.services.graph_nodes.invoke_gemma_llm",
            side_effect=["", '{"new_story": "복도에서 들은 소리\\n\\n근데 그때는 그냥 착각인 줄 알았어요."}'],
        ) as mocked_llm:
            result = generate_node(state)

        self.assertEqual(mocked_llm.call_count, 2)
        self.assertEqual(
            result["generated_story"],
            "복도에서 들은 소리\n\n근데 그때는 그냥 착각인 줄 알았어요.",
        )
        self.assertFalse(result["skip_evaluation"])

    def test_revision_prompt_prioritizes_removing_literary_style(self):
        prompt = build_revision_prompt(
            question="집 괴담",
            keywords=["집"],
            source_story={
                "name": "원본",
                "type": "horror_story",
                "regions": ["지역 미상"],
                "body": "집에서 이상한 일이 있었다.",
            },
            generated_story="그날 밤, 방 안은 완전히 어둠에 뒤덮여 있었다.",
            evaluation={"feedback": "문학체 표현이 강합니다."},
        )

        self.assertIn("소설 냄새를 빼고", prompt)
        self.assertIn("게시글스러움", prompt)
        self.assertIn('"new_story"', prompt)

    def test_automatic_penalties_cap_literary_story_score(self):
        evaluation = {
            "keyword_passed": True,
            "consistency_passed": True,
            "style_passed": True,
            "atmosphere_passed": True,
            "rewrite_required_by_editor": False,
            "criterion_scores": {
                "contradiction": 10,
                "reinterpretation": 10,
                "restraint": 10,
                "realism": 10,
                "tension_curve": 10,
                "cliche_avoidance": 10,
                "aftertaste": 10,
                "community_voice": 10,
                "anti_literary_style": 10,
            },
        }
        story = "어린 시절 그날 밤 완전히 어둠 속에서 몸이 떨렸다."

        penalized = apply_automatic_penalties(evaluation, story)

        self.assertEqual(penalized["score_total"], 74.0)
        self.assertFalse(is_evaluation_passed(penalized))
        self.assertTrue(penalized["automatic_penalties"])

    def test_evaluation_passes_only_when_all_required_scores_are_high_enough(self):
        evaluation = {
            "keyword_passed": True,
            "consistency_passed": True,
            "style_passed": True,
            "atmosphere_passed": True,
            "rewrite_required_by_editor": False,
            "criterion_scores": {
                "contradiction": 9,
                "reinterpretation": 9,
                "restraint": 9,
                "realism": 9,
                "tension_curve": 9,
                "cliche_avoidance": 9,
                "aftertaste": 9,
                "community_voice": 9,
                "anti_literary_style": 9,
            },
        }
        story = "근데 지금 생각하면 그때는 그냥 누가 깬 줄 알았음."

        evaluated = apply_automatic_penalties(evaluation, story)

        self.assertEqual(evaluated["score_total"], 90.0)
        self.assertTrue(is_evaluation_passed(evaluated))

    def test_tts_narration_prompt_keeps_story_and_limits_audio_tags(self):
        story = "복도에서 들은 소리\n\n근데 그때는 그냥 착각인 줄 알았어요."

        prompt = build_tts_narration_prompt(story)

        self.assertIn("낭독 대본", prompt)
        self.assertIn("[whispers]", prompt)
        self.assertIn("이야기의 내용, 사건, 순서, 결말을 바꾸지 마라.", prompt)
        self.assertIn("대본 텍스트만 출력하라.", prompt)
        self.assertIn(story, prompt)

    def test_convert_story_to_narration_falls_back_to_original_on_bad_response(self):
        story = "복도 괴담 본문. " * 20

        with patch(
            "archive.services.graph_nodes.invoke_gemma_llm",
            side_effect=["", RuntimeError("LLM down")],
        ):
            self.assertEqual(convert_story_to_narration(story), story)
            self.assertEqual(convert_story_to_narration(story), story)

    def test_convert_story_to_narration_strips_markdown_fence(self):
        story = "복도 괴담 본문. " * 20
        narration_body = "[whispers] 근데 그때는... 그냥 착각인 줄 알았어요. " * 10

        with patch(
            "archive.services.graph_nodes.invoke_gemma_llm",
            return_value=f"```\n{narration_body}\n```",
        ):
            narration = convert_story_to_narration(story)

        self.assertEqual(narration, narration_body.strip())
        self.assertNotIn("```", narration)

    def test_tts_payload_uses_v3_compatible_voice_settings(self):
        v3_payload = build_tts_payload("본문", "eleven_v3")

        self.assertEqual(v3_payload["model_id"], "eleven_v3")
        self.assertEqual(v3_payload["voice_settings"]["stability"], 0.0)
        self.assertNotIn("style", v3_payload["voice_settings"])
        self.assertNotIn("speed", v3_payload["voice_settings"])

    def test_tts_payload_rejects_non_v3_model(self):
        with self.assertRaisesMessage(
            ValueError,
            "ELEVENLABS_MODEL_ID는 eleven_v3로 설정해야 합니다.",
        ):
            build_tts_payload("본문", "eleven_multilingual_v2")

    def test_tts_stream_requires_eleven_v3_model(self):
        with patch.dict(
            "os.environ",
            {
                "ELEVENLABS_API_KEY": "test-key",
                "ELEVENLABS_VOICE_ID": "test-voice",
                "ELEVENLABS_MODEL_ID": "eleven_multilingual_v2",
            },
            clear=True,
        ):
            with self.assertRaisesMessage(
                ValueError,
                "ELEVENLABS_MODEL_ID는 eleven_v3로 설정해야 합니다.",
            ):
                open_story_audio_stream("본문")
