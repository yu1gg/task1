import json

import pytest
from app.services.interview_ai import evaluate_answer, build_report
from app.services.llm import LLMError
class Fake:
    def __init__(self, values): self.values = iter(values); self.calls = []
    def chat_json(self, system, user): self.calls.append(user); return next(self.values)
def result():
    return dict(scores=dict(technical=80, logic=70, communication=60, job_fit=90), feedback='有效反馈', quote='缓存', next_question='你提到缓存，如何失效？')
def test_evaluation_checks_quote_and_retries():
    bad = result(); bad['quote'] = '无中生有'
    llm = Fake([bad, result()])
    value = evaluate_answer({}, 'tech', [], '介绍项目', '我使用缓存', llm)
    assert value.scores.technical == 80
    assert len(llm.calls) == 2
    assert json.loads(llm.calls[0])["quote_hint"] == "我使用缓存"

def test_followup_uses_exact_transcript_when_model_omits_quote():
    value = result()
    del value["quote"]
    value["next_question"] = "你提到管理过20人团队，如何分工？"
    result_with_quote = evaluate_answer({}, "tech", [], "介绍项目", "我使用缓存", Fake([value]))
    assert result_with_quote.quote == "我使用缓存"
    assert result_with_quote.next_question == "你提到「我使用缓存」。请具体说明你的做法和结果。"


def test_valid_quote_does_not_allow_an_unanchored_fabricated_question():
    value = result()
    value["next_question"] = "你提到管理过20人团队，怎么分工的？"
    evaluation = evaluate_answer({}, "tech", [], "介绍项目", "我使用缓存", Fake([value]))
    assert evaluation.next_question == "你提到「缓存」。请具体说明你的做法和结果。"


@pytest.mark.parametrize("quote", ["缓存", "做法"])
def test_followup_is_available_when_model_returns_only_scores_feedback_and_quote(quote):
    value = result()
    del value["next_question"]
    value["quote"] = quote
    evaluation = evaluate_answer({}, "tech", [], "介绍项目", "我的做法是使用缓存", Fake([value]))
    assert evaluation.quote == quote
    assert evaluation.next_question == f"你提到「{quote}」。请具体说明你的做法和结果。"
    assert evaluation.scores.technical == 80


@pytest.mark.parametrize("quote", [False, 0, None, [], {}])
def test_malformed_quote_is_rejected_instead_of_treated_as_missing(quote):
    value = result()
    value.update(quote=quote, next_question="如何设计失效策略？")
    with pytest.raises(LLMError):
        evaluate_answer({}, "tech", [], "介绍项目", "我使用缓存", Fake([value] * 3))


def test_oversized_anchored_followup_falls_back_to_bounded_question():
    value = result()
    value["next_question"] = "问" * 500
    evaluation = evaluate_answer({}, "tech", [], "介绍项目", "我使用缓存", Fake([value]))
    assert evaluation.quote in "我使用缓存"
    assert evaluation.quote in evaluation.next_question
    assert len(evaluation.next_question) <= 500
    assert evaluation.scores.technical == 80


def test_invalid_scores_fail_safely():
    bad = result(); bad['scores']['technical'] = 101
    with pytest.raises(LLMError): evaluate_answer({}, 'tech', [], '问题', '缓存', Fake([bad]*3))
def test_report_computes_scores_without_llm_scoring():
    turns = [{'score_json': dict(technical=80, logic=60, communication=40, job_fit=20), 'ai_feedback': '反馈'}]
    report = build_report({'question_count':1}, 'tech', turns, Fake([dict(strengths=['清晰'], weaknesses=['深度'], suggestions=['练习1','练习2','练习3'], total_score=100)]))
    assert report['total_score'] == 50
    assert report['scores']['technical'] == 80
def test_final_answer_does_not_require_followup():
    value = result(); value.update(quote='', next_question='')
    assert evaluate_answer({}, 'hr', [], '问题', '回答', Fake([value]), final=True).next_question == ''

def test_report_rejects_incomplete_turns():
    with pytest.raises(LLMError): build_report({'question_count':2}, 'tech', [], Fake([]))

def test_whitespace_question_rejected():
    from app.services.interview_ai import generate_question
    with pytest.raises(LLMError): generate_question({}, 'tech', Fake([{'question':'   '}]*3))
