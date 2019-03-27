# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
System tests for queries.
"""

import operator

import pytest

import test_utils.system

from google.cloud import ndb

from . import KIND, OTHER_NAMESPACE


@pytest.mark.usefixtures("client_context")
def test_fetch_all_of_a_kind(ds_entity):
    for i in range(5):
        entity_id = test_utils.system.unique_resource_id()
        ds_entity(KIND, entity_id, foo=i)

    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()

    # query = SomeKind.query()  # Not implemented yet
    query = ndb.Query(kind=KIND)
    results = query.fetch()
    assert len(results) == 5

    results = sorted(results, key=operator.attrgetter("foo"))
    assert [entity.foo for entity in results] == [0, 1, 2, 3, 4]


@pytest.mark.usefixtures("client_context")
def test_fetch_lots_of_a_kind(dispose_of):
    n_entities = 500

    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()

    @ndb.tasklet
    def make_entities():
        entities = [SomeKind(foo=i) for i in range(n_entities)]
        keys = yield [entity.put_async() for entity in entities]
        return keys

    for key in make_entities().result():
        dispose_of(key._key)

    # query = SomeKind.query()  # Not implemented yet
    query = ndb.Query(kind=KIND)
    results = query.fetch()
    assert len(results) == n_entities

    results = sorted(results, key=operator.attrgetter("foo"))
    assert [entity.foo for entity in results][:5] == [0, 1, 2, 3, 4]


@pytest.mark.usefixtures("client_context")
def test_ancestor_query(ds_entity):
    root_id = test_utils.system.unique_resource_id()
    ds_entity(KIND, root_id, foo=-1)
    for i in range(5):
        entity_id = test_utils.system.unique_resource_id()
        ds_entity(KIND, root_id, KIND, entity_id, foo=i)

    another_id = test_utils.system.unique_resource_id()
    ds_entity(KIND, another_id, foo=42)

    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()

    query = ndb.Query(ancestor=ndb.Key(KIND, root_id))
    results = query.fetch()
    assert len(results) == 6

    results = sorted(results, key=operator.attrgetter("foo"))
    assert [entity.foo for entity in results] == [-1, 0, 1, 2, 3, 4]


@pytest.mark.usefixtures("client_context")
def test_projection(ds_entity):
    entity_id = test_utils.system.unique_resource_id()
    ds_entity(KIND, entity_id, foo=12, bar="none")
    entity_id = test_utils.system.unique_resource_id()
    ds_entity(KIND, entity_id, foo=21, bar="naan")

    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()
        bar = ndb.StringProperty()

    query = ndb.Query(kind=KIND, projection=("foo",))
    results = query.fetch()
    assert len(results) == 2

    results = sorted(results, key=operator.attrgetter("foo"))

    assert results[0].foo == 12
    with pytest.raises(ndb.UnprojectedPropertyError):
        results[0].bar

    assert results[1].foo == 21
    with pytest.raises(ndb.UnprojectedPropertyError):
        results[1].bar


@pytest.mark.usefixtures("client_context")
def test_distinct_on(ds_entity):
    for i in range(6):
        entity_id = test_utils.system.unique_resource_id()
        ds_entity(KIND, entity_id, foo=i % 2, bar="none")

    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()
        bar = ndb.StringProperty()

    query = ndb.Query(kind=KIND, distinct_on=("foo",))
    results = query.fetch()
    assert len(results) == 2

    results = sorted(results, key=operator.attrgetter("foo"))

    assert results[0].foo == 0
    assert results[0].bar == "none"

    assert results[1].foo == 1
    assert results[1].bar == "none"


@pytest.mark.usefixtures("client_context")
def test_namespace(dispose_of):
    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()
        bar = ndb.StringProperty()

    entity1 = SomeKind(foo=1, bar="a", namespace=OTHER_NAMESPACE)
    entity1.put()
    dispose_of(entity1.key._key)

    entity2 = SomeKind(foo=2, bar="b")
    entity2.put()
    dispose_of(entity2.key._key)

    query = ndb.Query(kind=KIND, namespace=OTHER_NAMESPACE)
    results = query.fetch()
    assert len(results) == 1

    assert results[0].foo == 1
    assert results[0].bar == "a"
    assert results[0].key.namespace() == OTHER_NAMESPACE


@pytest.mark.usefixtures("client_context")
def test_filter_equal(ds_entity):
    for i in range(5):
        entity_id = test_utils.system.unique_resource_id()
        ds_entity(KIND, entity_id, foo=i)

    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()

    # query = SomeKind.query()  # Not implemented yet
    query = ndb.Query(kind=KIND).filter(SomeKind.foo == 2)
    results = query.fetch()
    assert len(results) == 1
    assert results[0].foo == 2


@pytest.mark.usefixtures("client_context")
def test_filter_not_equal(ds_entity):
    for i in range(5):
        entity_id = test_utils.system.unique_resource_id()
        ds_entity(KIND, entity_id, foo=i)

    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()

    # query = SomeKind.query()  # Not implemented yet
    query = ndb.Query(kind=KIND).filter(SomeKind.foo != 2)
    results = query.fetch()
    assert len(results) == 4

    results = sorted(results, key=operator.attrgetter("foo"))
    assert [entity.foo for entity in results] == [0, 1, 3, 4]


@pytest.mark.usefixtures("client_context")
def test_filter_or(dispose_of):
    class SomeKind(ndb.Model):
        foo = ndb.IntegerProperty()
        bar = ndb.StringProperty()

    @ndb.tasklet
    def make_entities():
        keys = yield (
            SomeKind(foo=1, bar="a").put_async(),
            SomeKind(foo=2, bar="b").put_async(),
            SomeKind(foo=1, bar="c").put_async(),
        )
        for key in keys:
            dispose_of(key._key)

    make_entities().check_success()
    query = ndb.Query(kind=KIND).filter(
        ndb.OR(SomeKind.foo == 1, SomeKind.bar == "c")
    )
    results = query.fetch()
    assert len(results) == 2

    results = sorted(results, key=operator.attrgetter("foo"))
    assert [entity.bar for entity in results] == ["a", "c"]
