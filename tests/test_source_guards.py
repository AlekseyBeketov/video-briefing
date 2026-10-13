"""Small invented examples exercise source-derived guards without gold answer fixtures."""
from copy import deepcopy
from dataclasses import replace

import pytest

from video_briefing import briefing, qa
from video_briefing.grounding import audit_claims
from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.source_guards import (
    claim_source_context, coordinated_quantity_conflicts, preserve_example_quantities, quantities,
    repair_coordinated_quantities, software_interpretation_context, source_sentences,
    validate_preserved_quantities,
    preserve_source_uncertainty, validate_preserved_uncertainty,
)
from test_generation_coverage import SequenceLLM, draft, explicit_checks


def bundle(rows):
    return EvidenceBundle('youtube', 'DvSwvJVens8', 'https://youtube.com/watch?v=DvSwvJVens8',
                          'en', 'fixture', 'captions', 'test', [
                              TranscriptSegment(str(i), text, start, 2) for i, (text, start) in enumerate(rows)
                          ], 'a' * 64)


def numeric_source():
    return bundle([
        ('Model Example has 17 billion parameters.', 0),
        ('For each request 2,3 billion are active.', 2),
        ('It needs 64 GB of memory.', 4),
        ('Unrelated example needs 99 GB.', 30),
    ])


def example_draft():
    value = draft()
    value['gist_evidence'] = ['0']
    value['coverage']['worked_examples'] = [{
        'text': 'Model Example has 17 billion parameters and requires 64 GB.',
        'evidence': ['0', '2'], 'kind': 'source', 'quantities': [
            {'text': '17 billion total parameters', 'evidence': ['0']},
            {'text': '64 GB of storage', 'evidence': ['2']},
        ],
    }]
    return value


def test_missing_intermediate_quantity_survives_even_when_false_positive_auditor_says_explicit():
    source = numeric_source()
    result, metadata = briefing.brief_bundle(source, SequenceLLM([example_draft(), explicit_checks(2)]))
    example = result['useful_ideas'][0]
    assert '2,3 billion are active' in example['text']
    assert '99' not in example['text']
    assert {e['id'] for e in example['evidence']} == {'0', '1', '2'}
    assert metadata['deterministic_source_repairs'][0]['kind'] == 'extractive_quantity_preservation'


def test_preservation_is_idempotent_and_never_replaces_source_with_gold():
    source, value = numeric_source(), example_draft()
    before = deepcopy(source)
    assert preserve_example_quantities(value, source, source.segments)
    assert preserve_example_quantities(value, source, source.segments) == []
    assert source == before
    assert quantities('2.3 billion') == quantities('2,3 млрд')
    assert quantities('MXFP4 GPT OSS 120B RTX 5090') == set()


def test_numeric_preservation_runs_after_invalid_example_citations_are_repaired():
    source = numeric_source()
    value = example_draft()
    value['coverage']['worked_examples'][0]['evidence'] = ['unknown']
    model = SequenceLLM([
        value, {'citation_repairs': [{'claim_index': 1, 'evidence': ['0', '2']}]},
        explicit_checks(2),
    ])
    result, metadata = briefing.brief_bundle(source, model)
    assert '2,3 billion are active' in result['useful_ideas'][0]['text']
    assert {e['id'] for e in result['useful_ideas'][0]['evidence']} == {'0', '1', '2'}
    assert metadata['deterministic_source_repairs'][0]['kind'] == 'extractive_quantity_preservation'
    assert len(model.requests) == 3


def test_atomic_quantity_citation_repairs_cannot_borrow_unprovided_inventory_rows(monkeypatch):
    source, value = numeric_source(), example_draft()
    value['coverage']['worked_examples'][0]['quantities'][0]['evidence'] = ['unknown']
    monkeypatch.setattr(briefing, 'retrieve', lambda *a, **kw: source.segments)
    model = SequenceLLM([{'citation_repairs': [{'claim_index': 2, 'evidence': ['3']}]}])
    with pytest.raises(ValueError, match='outside its supplied source context'):
        # Both bounded attempts fail closed; the source repair must not see row 3.
        model.responses_to_return *= 2
        briefing._repair_citations(value, source, model, {'0', '1', '2'})
    for request in model.requests:
        assert 'Unrelated example' not in request['prompt']
    assert value['coverage']['worked_examples'][0]['quantities'][0]['evidence'] == ['unknown']


def test_auditor_cannot_silently_drop_a_required_source_preservation():
    with pytest.raises(ValueError, match='dropped a preserved'):
        briefing.brief_bundle(numeric_source(), SequenceLLM([example_draft(), {
            'checks': [{'index': 0, 'support': 'explicit'}, {'index': 1, 'support': 'unsupported'}],
        }]))
    repair = {'kind': 'extractive_quantity_preservation', 'quantities': [('2.3', 'billion')], 'evidence': ['1']}
    with pytest.raises(ValueError, match='dropped a preserved'):
        validate_preserved_quantities([{'text': '2.3 billion parameters', 'evidence': ['3']}], [repair])


def test_same_scalar_and_ids_cannot_replace_the_preserved_role_or_original_phrase():
    value, source = example_draft(), numeric_source()
    repairs = preserve_example_quantities(value, source, source.segments)
    with pytest.raises(ValueError, match='dropped a preserved'):
        validate_preserved_quantities([{'text': '2.3 billion total parameters', 'evidence': ['1']}], repairs)
    preserved = value['coverage']['worked_examples'][0]['quantities'][-1]
    validate_preserved_quantities([preserved], repairs)


def test_sparse_cross_topic_example_does_not_receive_unconditional_numbers():
    source = numeric_source()
    value = example_draft()
    value['coverage']['worked_examples'][0]['evidence'] = ['0', '3']
    assert preserve_example_quantities(value, source, source.segments) == []


def test_no_unprovided_sentence_or_time_gap_is_joined():
    source = bundle([('Incomplete Example', 0), ('has 2.3 billion active parameters.', 60)])
    sentences = source_sentences(source, source.segments)
    assert len(sentences) == 2 and sentences[0].run != sentences[1].run
    assert all(len(s.ids) == 1 for s in sentences)
    source = numeric_source()
    assert all('1' not in sentence.ids for sentence in source_sentences(source, source.segments[::2]))


def shared_source():
    return bundle([
        ('AAA Box is for researchers.', 0),
        ('It supports models up to 23 billion parameters.', 2),
        ('BBB Box is a related architecture in ordinary laptops.', 4),
    ])


@pytest.mark.parametrize('conjunction', ['or', 'and', 'или', 'и'])
def test_shared_ceiling_is_not_accepted_by_a_false_positive_auditor(conjunction):
    source = shared_source()
    claim = {'text': f'AAA Box {conjunction} BBB Box support up to 23 billion parameters.', 'evidence': ['0', '1', '2']}
    labels, _ = audit_claims(source, [claim], SequenceLLM([explicit_checks(1)]))
    assert labels == ['unsupported']
    assert coordinated_quantity_conflicts(claim, source, source.segments)


def test_entity_on_other_side_of_a_time_gap_cannot_supply_a_quantity_subject():
    source = bundle([('AAA Box and BBB Box are available.', 0), ('It supports 23 billion parameters.', 60)])
    claim = {'text': 'AAA Box or BBB Box supports 23 billion parameters.', 'evidence': ['0', '1']}
    # This narrow guard does not certify an unanchored quantity as supported.
    # General audit still has to reject absent semantics; no cross-gap subject is used.
    assert coordinated_quantity_conflicts(claim, source, source.segments) == []
    sentences = source_sentences(source, source.segments)
    assert sentences[0].run != sentences[1].run


def test_legitimate_shared_or_separately_supported_quantity_is_not_rejected():
    source = bundle([('AAA Box and BBB Box support 23 billion parameters.', 0)])
    claim = {'text': source.segments[0].text, 'evidence': ['0']}
    assert coordinated_quantity_conflicts(claim, source, source.segments) == []
    source = bundle([('AAA Box supports 23 billion parameters.', 0), ('BBB Box also supports 23 billion parameters.', 2)])
    assert coordinated_quantity_conflicts({**claim, 'evidence': ['0', '1']}, source, source.segments) == []


def test_repair_keeps_only_the_exact_narrower_source_relation():
    source = shared_source()
    claim = {'text': 'AAA Box or BBB Box supports 23 billion parameters.', 'evidence': ['0', '1', '2'], 'kind': 'source'}
    repairs = repair_coordinated_quantities([claim], source, source.segments)
    assert len(repairs) == 1
    assert 'BBB' not in claim['text'] and 'AAA Box is for researchers.' in claim['text']
    assert claim['evidence'] == ['0', '1']
    assert coordinated_quantity_conflicts(claim, source, source.segments) == []
    assert repair_coordinated_quantities([claim], source, source.segments) == []


def test_single_subject_cannot_inherit_another_subjects_ceiling():
    source = shared_source()
    claim = {'text': 'BBB Box supports 23 billion parameters.', 'evidence': ['0', '1', '2']}
    assert coordinated_quantity_conflicts(claim, source, source.segments)
    labels, _ = audit_claims(source, [claim], SequenceLLM([explicit_checks(1)]))
    assert labels == ['unsupported']


def test_named_quantity_subject_does_not_borrow_previous_catalogue_subjects():
    source = bundle([
        ('AAA Box and BBB Box are discussed.', 0),
        ('AAA Box supports 23 billion parameters.', 2),
    ])
    claim = {'text': 'AAA Box and BBB Box support 23 billion parameters.', 'evidence': ['0', '1']}
    assert coordinated_quantity_conflicts(claim, source, source.segments)
    assert not coordinated_quantity_conflicts({**claim, 'text': source.segments[1].text}, source, source.segments)


def test_distinct_ledger_clauses_do_not_transfer_every_quantity_to_the_heading():
    source = bundle([
        ('AAA Box includes BBB Core.', 0),
        ('It needs 23 GB of memory.', 2),
        ('BBB Core reserves 7 GB for graphics.', 4),
    ])
    claim = {'text': 'AAA Box with BBB Core; 23 GB of memory; BBB Core reserves 7 GB for graphics.',
             'evidence': ['0', '1', '2'], 'kind': 'source'}
    before = deepcopy(claim)
    assert repair_coordinated_quantities([claim], source, source.segments) == []
    assert claim == before


def test_brief_repair_runs_before_auditor_and_qa_rejects_the_same_wrong_relationship(monkeypatch):
    source = shared_source()
    value = draft()
    value['gist_evidence'] = ['0']
    value['useful_ideas'] = [{'text': 'AAA Box or BBB Box supports 23 billion parameters.', 'evidence': ['0', '1', '2'], 'kind': 'source'}]
    model = SequenceLLM([value, explicit_checks(2)])
    result, info = briefing.brief_bundle(source, model)
    assert 'BBB' not in result['useful_ideas'][0]['text']
    assert info['deterministic_source_repairs'][0]['kind'] == 'extractive_relationship_repair'
    monkeypatch.setattr(qa, 'retrieve', lambda *a, **kw: source.segments)
    value = {'answer': 'Untrusted', 'answer_supported': True, 'claims': [{**value['useful_ideas'][0], 'kind': 'author_statement'}], 'qualifications': {name: [] for name in qa.QUALIFICATION_FACETS}}
    result = qa.answer_question(source, 'model capacity', SequenceLLM([value, explicit_checks(1)]))
    assert result['abstained'] and not result['claims']


def test_missing_acronym_keeps_earlier_software_context_despite_auditor_omission():
    source = bundle([
        ('Vendor has a software ecosystem for researchers.', 0),
        ('Unrelated Other software ecosystem is also discussed.', 2),
        ('Vendor prices are high. If you need, choose AAA Box.', 10),
    ])
    claim = {'text': 'If XYZ is required, choose Vendor AAA Box.', 'evidence': ['2']}
    assert software_interpretation_context(claim, source, source.segments) == ['0']
    labels, evidence = audit_claims(source, [claim], SequenceLLM([{'checks': [{'index': 0, 'support': 'explicit', 'evidence': ['2']}]}]))
    assert labels == ['inference'] and evidence == [['2', '0']]
    assert software_interpretation_context(claim, source, source.segments[1:]) == []
    # The vendor software context does not mention XYZ; no downgrade is undone.
    assert 'XYZ' not in source.segments[0].text


@pytest.mark.parametrize('condition', ['При необходимости в', 'Если нужна', 'When required:'])
def test_conditional_variants_cannot_promote_a_missing_prerequisite(condition):
    source = bundle([
        ('Vendor has a software ecosystem for researchers.', 0),
        ('If you need, choose Vendor AAA Box.', 10),
    ])
    claim = {'text': f'{condition} XYZ, choose Vendor AAA Box.', 'evidence': ['1']}
    labels, ids = audit_claims(source, [claim], SequenceLLM([explicit_checks(1)]))
    assert labels == ['inference'] and set(ids[0]) == {'0', '1'}


def test_context_uses_vendor_in_cited_sentence_continuation_not_neighbour_padding():
    source = bundle([
        ('Vendor has a software ecosystem for researchers.', 0),
        ('If you need, choose AAA Box, all from', 10),
        ('Vendor.', 12),
    ])
    claim = {'text': 'If XYZ is required, choose AAA Box.', 'evidence': ['1']}
    assert software_interpretation_context(claim, source, source.segments) == ['0']
    labels, ids = audit_claims(source, [claim], SequenceLLM([{
        'checks': [{'index': 0, 'support': 'explicit', 'evidence': ['1']}],
    }]))
    assert labels == ['inference'] and set(ids[0]) == {'0', '1', '2'}
    assert not software_interpretation_context(claim, source, source.segments[:2])
    source.segments[2] = replace(source.segments[2], start_seconds=60)
    assert not software_interpretation_context(claim, source, source.segments)


def test_auditor_cannot_drop_later_independent_numeric_clause_context():
    source = bundle([
        ('Alpha model requires 17 GB of memory.', 0),
        ('Different unrelated device costs 99 GB.', 30),
        ('Beta model generates 23 tokens/s.', 60),
    ])
    claim = {'text': 'Alpha model requires 17 GB; Beta model generates 23 tokens/s.',
             'evidence': ['0', '2']}
    assert set(claim_source_context(claim, source, source.segments)) == {'0', '2'}
    labels, ids = audit_claims(source, [claim], SequenceLLM([{
        'checks': [{'index': 0, 'support': 'explicit', 'evidence': ['0']}],
    }]))
    assert labels == ['explicit'] and set(ids[0]) == {'0', '2'}
    assert claim_source_context(claim, source, source.segments[:2]) == ['0']


def test_missing_vendor_uses_exact_source_product_bridge_for_software_provenance():
    source = bundle([
        ('Vendor provides a software ecosystem for research.', 0),
        ('Vendor announced AAA Box.', 20),
        ('If you need, choose AAA Box.', 40),
    ])
    claim = {'text': 'If XYZ is required, choose AAA Box.', 'evidence': ['2']}
    assert set(software_interpretation_context(claim, source, source.segments)) == {'0', '1'}
    labels, ids = audit_claims(source, [claim], SequenceLLM([explicit_checks(1)]))
    assert labels == ['inference'] and set(ids[0]) == {'0', '1', '2'}
    assert not software_interpretation_context(claim, source, [source.segments[0], source.segments[2]])
    assert not software_interpretation_context({**claim, 'text': 'If XYZ is required, choose AAA Different.'}, source, source.segments)


def test_explicit_untested_qualification_is_preserved_only_for_exact_source_product():
    source = bundle([
        ('Vendor announced AAA Box.', 0),
        ('No performance measurements are available.', 2),
        ('BBB Box has not been tested.', 30),
    ])
    value = draft()
    value['topics'] = [{'text': 'AAA Box is discussed.', 'evidence': ['0']}]
    repairs = preserve_source_uncertainty(value, source, source.segments)
    assert len(repairs) == 1
    assert value['caveats'][0]['evidence'] == ['0', '1']
    assert 'BBB' not in value['caveats'][0]['text']
    assert preserve_source_uncertainty(value, source, source.segments) == repairs
    assert len(value['caveats']) == 1
    validate_preserved_uncertainty(value['caveats'], repairs)
    with pytest.raises(ValueError, match='preserved original source qualification'):
        validate_preserved_uncertainty([], repairs)
    source.segments[1] = replace(source.segments[1], start_seconds=60)
    assert not preserve_source_uncertainty({'topics': value['topics']}, source, source.segments)


def test_false_positive_auditor_cannot_erase_preserved_uncertainty():
    source = bundle([('AAA Box is discussed.', 0), ('It has not been tested.', 2)])
    value = draft()
    value['gist_evidence'] = ['0']
    value['topics'] = [{'text': 'AAA Box is discussed.', 'evidence': ['0']}]
    result, metadata = briefing.brief_bundle(source, SequenceLLM([value, explicit_checks(3)]))
    assert 'It has not been tested.' in result['caveats'][0]['text']
    assert metadata['deterministic_source_repairs'][0]['kind'] == 'extractive_uncertainty_preservation'
    with pytest.raises(ValueError, match='preserved original source qualification'):
        briefing.brief_bundle(source, SequenceLLM([value, {
            'checks': [{'index': 0, 'support': 'explicit'}, {'index': 1, 'support': 'explicit'},
                       {'index': 2, 'support': 'unsupported'}],
        }]))
