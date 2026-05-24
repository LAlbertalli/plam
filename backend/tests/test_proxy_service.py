import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.domain import LLMModel, ModelRegexRule, RegexChainEnum
from app.services.proxy_service import proxy_service
from tests.conftest import TestingSessionLocal

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Clear tables after each test to ensure isolation
        db.query(ModelRegexRule).delete()
        db.query(LLMModel).delete()
        db.commit()
        db.close()

def test_proxy_service_input_chain_ordering(db_session: Session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # Rule 1 has order 2: apple -> banana
    rule_1 = ModelRegexRule(
        model_id=model.id,
        name="Rule 1",
        pattern=r"apple",
        replacement="banana",
        chain=RegexChainEnum.input_chain,
        order=2
    )
    # Rule 2 has order 1: banana -> cherry
    rule_2 = ModelRegexRule(
        model_id=model.id,
        name="Rule 2",
        pattern=r"banana",
        replacement="cherry",
        chain=RegexChainEnum.input_chain,
        order=1
    )
    db_session.add(rule_1)
    db_session.add(rule_2)
    db_session.commit()

    # Because Rule 2 runs first (order 1), it doesn't match "apple".
    # Then Rule 1 runs (order 2) and replaces "apple" with "banana".
    # The final output should be "banana" (proving order is respected).
    result = proxy_service.apply_input_chain("apple", model.id, db_session)
    assert result == "banana"

def test_proxy_service_sequential_chaining(db_session: Session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # Rule 1 has order 1: apple -> banana
    rule_1 = ModelRegexRule(
        model_id=model.id,
        name="Rule 1",
        pattern=r"apple",
        replacement="banana",
        chain=RegexChainEnum.input_chain,
        order=1
    )
    # Rule 2 has order 2: banana -> cherry
    rule_2 = ModelRegexRule(
        model_id=model.id,
        name="Rule 2",
        pattern=r"banana",
        replacement="cherry",
        chain=RegexChainEnum.input_chain,
        order=2
    )
    db_session.add(rule_1)
    db_session.add(rule_2)
    db_session.commit()

    # Because Rule 1 runs first (order 1), it changes "apple" to "banana".
    # Then Rule 2 runs (order 2), matches "banana", and changes it to "cherry".
    result = proxy_service.apply_input_chain("apple", model.id, db_session)
    assert result == "cherry"

def test_proxy_service_inactive_rules(db_session: Session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    rule = ModelRegexRule(
        model_id=model.id,
        name="Rule",
        pattern=r"apple",
        replacement="banana",
        chain=RegexChainEnum.input_chain,
        order=1,
        is_active=False
    )
    db_session.add(rule)
    db_session.commit()

    result = proxy_service.apply_input_chain("apple", model.id, db_session)
    assert result == "apple"

def test_proxy_service_output_chain(db_session: Session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # Rule in output chain
    rule_out = ModelRegexRule(
        model_id=model.id,
        name="OutRule",
        pattern=r"secret_key",
        replacement="REDACTED",
        chain=RegexChainEnum.output_chain,
        order=1
    )
    # Rule in input chain (should be ignored by output chain processing)
    rule_in = ModelRegexRule(
        model_id=model.id,
        name="InRule",
        pattern=r"secret_key",
        replacement="SHOULD_NOT_HAPPEN",
        chain=RegexChainEnum.input_chain,
        order=1
    )
    db_session.add(rule_out)
    db_session.add(rule_in)
    db_session.commit()

    result = proxy_service.apply_output_chain("My secret_key is 123", model.id, db_session)
    assert result == "My REDACTED is 123"

def test_proxy_service_regex_capture_groups(db_session: Session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # Rule that captures text and references it in replacement
    rule = ModelRegexRule(
        model_id=model.id,
        name="CaptureRule",
        pattern=r"user_(\d+)",
        replacement=r"ID: \1",
        chain=RegexChainEnum.input_chain,
        order=1
    )
    db_session.add(rule)
    db_session.commit()

    result = proxy_service.apply_input_chain("Access requested by user_48291 and user_112.", model.id, db_session)
    assert result == "Access requested by ID: 48291 and ID: 112."

def test_proxy_service_global_replacement(db_session: Session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # Rule that should match all occurrences
    rule = ModelRegexRule(
        model_id=model.id,
        name="GlobalRule",
        pattern=r"apple",
        replacement="banana",
        chain=RegexChainEnum.input_chain,
        order=1
    )
    db_session.add(rule)
    db_session.commit()

    result = proxy_service.apply_input_chain("apple pie, apple cider, and apple juice.", model.id, db_session)
    assert result == "banana pie, banana cider, and banana juice."

def test_proxy_service_regex_error_handling(db_session: Session):
    model = LLMModel(
        id=uuid4(),
        name="TestModel",
        hf_repo_id="test/repo",
        gguf_filename="test.gguf",
        ram_required_mb=1000,
        context_size=2048
    )
    db_session.add(model)
    db_session.commit()

    # Rule with invalid regex pattern
    invalid_input_rule = ModelRegexRule(
        model_id=model.id,
        name="InvalidInputRule",
        pattern=r"(",
        replacement="banana",
        chain=RegexChainEnum.input_chain,
        order=1
    )
    invalid_output_rule = ModelRegexRule(
        model_id=model.id,
        name="InvalidOutputRule",
        pattern=r"(",
        replacement="banana",
        chain=RegexChainEnum.output_chain,
        order=1
    )
    db_session.add(invalid_input_rule)
    db_session.add(invalid_output_rule)
    db_session.commit()

    result_input = proxy_service.apply_input_chain("apple", model.id, db_session)
    assert result_input == "apple"

    result_output = proxy_service.apply_output_chain("apple", model.id, db_session)
    assert result_output == "apple"
