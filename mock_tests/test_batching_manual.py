import uuid

import weaviate


def test_manual_batching_warning_object(recwarn, weaviate_mock):
    weaviate_mock.expect_request("/v1/batch/objects").respond_with_json({})

    client = weaviate.Client(url="http://127.0.0.1:23534")

    client.batch.add_data_object({}, "ExistingClass")
    client.batch.create_objects()

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, DeprecationWarning)
    assert str(w.message).startswith("Dep002")


def test_manual_batching_warning_ref(recwarn, weaviate_mock):
    weaviate_mock.expect_request("/v1/batch/references").respond_with_json({})

    client = weaviate.Client(url="http://127.0.0.1:23534")
    client.batch.add_reference(
        str(uuid.uuid4()), "NonExistingClass", "existsWith", str(uuid.uuid4()), "OtherClass"
    )
    client.batch.create_references()

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, DeprecationWarning)
    assert str(w.message).startswith("Dep002")