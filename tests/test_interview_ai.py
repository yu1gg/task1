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
