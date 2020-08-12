import unittest
import weaviate

import copy
import os
from test.testing_util import replace_connection, add_run_rest_to_mock
from weaviate.connect import REST_METHOD_POST, REST_METHOD_DELETE, REST_METHOD_GET
from weaviate import SEMANTIC_TYPE_ACTIONS
from unittest.mock import Mock
from weaviate.exceptions import SchemaValidationException

company_test_schema = {
  "actions": {
    "classes": [],
    "type": "action"
  },
  "things": {
    "@context": "",
    "version": "0.2.0",
    "type": "thing",
    "name": "company",
    "maintainer": "yourfriends@weaviate.com",
    "classes": [
      {
        "class": "Company",
        "description": "A business that acts in the market",
        "keywords": [],
        "properties": [
          {
            "name": "name",
            "description": "The name under which the company is known",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "legalBody",
            "description": "The legal body under which the company maintains its business",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "hasEmployee",
            "description": "The employees of the company",
            "dataType": [
              "Employee"
            ],
            "cardinality": "many",
            "keywords": []
          }
        ]
      },
      {
        "class": "Employee",
        "description": "An employee of the company",
        "keywords": [],
        "properties": [
          {
            "name": "name",
            "description": "The name of the employee",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "job",
            "description": "the job description of the employee",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "yearsInTheCompany",
            "description": "The number of years this employee has worked in the company",
            "dataType": [
              "int"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          }
        ]
      }
    ]
  }
}

# A test schema as it was returned from a real weaviate instance
persons_return_test_schema = {
    "actions": {
        "classes": [],
        "type": "action"
    },
    "things": {
        "classes": [
            {
                "class": "Person",
                "description": "A person such as humans or personality known through culture",
                "properties": [
                    {
                        "cardinality": "atMostOne",
                        "dataType": [
                            "text"
                        ],
                        "description": "The name of this person",
                        "name": "name"
                    }
                ]
            },
            {
                "class": "Group",
                "description": "A set of persons who are associated with each other over some common properties",
                "properties": [
                    {
                        "cardinality": "atMostOne",
                        "dataType": [
                            "text"
                        ],
                        "description": "The name under which this group is known",
                        "name": "name"
                    },
                    {
                        "cardinality": "many",
                        "dataType": [
                            "Person"
                        ],
                        "description": "The persons that are part of this group",
                        "name": "members"
                    }
                ]
            }
        ],
        "type": "thing"
    }
}

# Schema containing explicit index
person_index_false_schema = {
  "actions": {
    "classes": [],
    "type": "action"
  },
  "things": {
    "@context": "",
    "version": "0.2.0",
    "type": "thing",
    "name": "people",
    "maintainer": "yourfriends@weaviate.com",
    "classes": [
      {
        "class": "Person",
        "description": "A person such as humans or personality known through culture",
        "keywords": [],
        "properties": [
          {
            "name": "name",
            "description": "The name of this person",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": [],
            "index": False
          }
        ]
      },
      {
        "class": "Group",
        "description": "A set of persons who are associated with each other over some common properties",
        "keywords": [],
        "properties": [
          {
            "name": "name",
            "description": "The name under which this group is known",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": [],
            "index": True
          },
          {
            "name": "members",
            "description": "The persons that are part of this group",
            "dataType": [
              "Person"
            ],
            "cardinality": "many"
          }
        ]
      }
    ]
  }
}


stop_vectorization_schema = {
  "actions": {
    "classes": [],
    "type": "action"
  },
  "things": {
    "@context": "",
    "version": "0.2.0",
    "type": "thing",
    "name": "data",
    "maintainer": "yourfriends@weaviate.com",
    "classes": [
      {
        "class": "DataType",
        "description": "DataType",
        "keywords": [],
        "vectorizeClassName": False,
        "properties": [
          {
            "name": "owner",
            "description": "the owner",
            "dataType": [
              "text"
            ],
            "keywords": [],
            "vectorizePropertyName": False,
            "index": False
          },
          {
            "name": "complexDescription",
            "description": "Description of the complex type",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": [],
            "vectorizePropertyName": False,
          },
          {
            "name": "hasPrimitives",
            "description": "The primitive data points",
            "dataType": [
              "Primitive"
            ],
            "cardinality": "many",
            "keywords": []
          }
        ]
      },

      {
        "class": "Primitive",
        "description": "DataType",
        "keywords": [],
        "vectorizeClassName": True,
        "properties": [
          {
            "name": "type",
            "description": "the primitive type",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": [],
          }
        ]
      }
    ]
  }
}


class TestSchema(unittest.TestCase):
    def test_create_schema_invalid_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.schema.create(None)
            self.fail("No exception when no valid schema given")
        except TypeError:
            pass # Expected value error
        try:
            w.schema.create("/random/noFile")  # No valid file or url
            self.fail("No exception when no valid schema given")
        except ValueError:
            pass # Expected value error
        try:
            w.schema.create(42)  # No valid type
            self.fail("No exception when no valid schema given")
        except TypeError:
            pass # Expected value error
            # Load from URL

    # @patch('weaviate.client._get_dict_from_object')
    # def mock_get_dict_from_object(self, object_):
    #     return company_test_schema

    def test_create_schema_load_file(self):
        w = weaviate.Client("http://localhost:8080")

        # Load from URL
        # TODO ??? HOW TO PATCH THIS SHIT
        # with patch('weaviate.util._get_dict_from_object') as mock_util:
        #     # Mock weaviate.client._get_dict_from_object the function where
        #     # it is looked up see https://docs.python.org/3/library/unittest.mock.html#where-to-patch
        #     # for more information
        #
        #     connection_mock_url = Mock()  # Mock weaviate.connection
        #     w._connection = connection_mock_url
        #     add_run_rest_to_mock(connection_mock_url)
        #
        #     mock_util.return_value = company_test_schema
        #
        #     w.schema.create("http://semi.technology/schema")
        #     mock_util.assert_called()
        #     connection_mock_url.run_rest.assert_called()


        # Load from file
        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file)
        replace_connection(w, add_run_rest_to_mock(connection_mock_file))  # Replace connection with mock

        current_dir = os.path.dirname(__file__)
        schema_json_file = os.path.join(current_dir, "schema_company.json")
        w.schema.create(schema_json_file)  # Load from file
        connection_mock_file.run_rest.assert_called()  # See if mock has been called

        # Load dict
        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        replace_connection(w, add_run_rest_to_mock(connection_mock_dict))
        w.schema.create(company_test_schema)
        connection_mock_dict.run_rest.assert_called()

        # Test schema missing actions/schema
        # Mock run_rest
        connection_mock = Mock()
        replace_connection(w, add_run_rest_to_mock(connection_mock))
        schema = copy.deepcopy(company_test_schema)
        # Remove actions
        del schema[weaviate.SEMANTIC_TYPE_ACTIONS]
        w.schema.create(company_test_schema)

        schema = copy.deepcopy(company_test_schema)
        del schema[weaviate.SEMANTIC_TYPE_THINGS]
        w.schema.create(company_test_schema)
        connection_mock.run_rest.assert_called()

    def test_run_rest_failed(self):
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, return_json={"Test error"}, status_code=500)
        replace_connection(w, connection_mock)

        try:
            w.schema.create(company_test_schema)
        except weaviate.UnexpectedStatusCodeException:
            pass  # Expected exception

    def test_get_schema(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        replace_connection(w, connection_mock_file)  # Replace connection with mock

        schema = w.schema.get()
        connection_mock_file.run_rest.assert_called()  # See if mock has been called
        self.assertTrue("things" in schema)
        self.assertEqual(len(schema["things"]["classes"]), 2)

    def test_create_schema_with_explicit_index(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        replace_connection(w, connection_mock_dict)
        w.schema.create(person_index_false_schema)
        connection_mock_dict.run_rest.assert_called()

    def test_not_indexed_class_name(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        replace_connection(w, connection_mock_dict)
        w.schema.create(stop_vectorization_schema)
        connection_mock_dict.run_rest.assert_called()

    def test_invalid_schema(self):
        schema = {
            "class": "Category",
            "description": "Category an article is a type off",
            "properties": [
              {
                "cardinality": "atMostOne",
                "dataType": [
                  "text"
                ],
                "description": "category name",
                "name": "name"
              }
            ]
        }
        w = weaviate.Client("http://localhost:1234")
        try:
            w.schema.create(schema)
            self.fail("Expected SchemaValidationException")
        except weaviate.SchemaValidationException:
            pass


class TestContainsSchema(unittest.TestCase):

    def test_contains_a_schema(self):
        # If a schema is present it should return true otherwise false
        # 1. test schema is present:
        w = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        replace_connection(w, connection_mock_file)

        self.assertTrue(w.schema.contains())

        # 2. test no schema is present:
        w = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        empty_schema = {"actions":{"classes":[],"type":"action"},"things":{"classes":[],"type":"thing"}}
        add_run_rest_to_mock(connection_mock_file, empty_schema)
        replace_connection(w, connection_mock_file)

        self.assertFalse(w.schema.contains())

    def test_contains_specific_schema(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        replace_connection(w, connection_mock_file)
        self.assertFalse(w.schema.contains(company_test_schema))
        subset_schema = {
            "things": {
                "classes": [
                    {
                        "class": "Person",
                        "description": "",
                        "properties": [{
                                "cardinality": "atMostOne",
                                "dataType": ["text"],
                                "description": "",
                                "name": "name"
                            }
                        ]
                    }
                ]
            }
        }
        self.assertTrue(w.schema.contains(subset_schema))


class TestCreate(unittest.TestCase):

    def test_create_single_class(self):
        group_class = {
            "class": "Group",
            "description": "A set of persons who are associated with each other over some common properties",
            "keywords": [],
            "properties": [
                {
                    "name": "name",
                    "description": "The name under which this group is known",
                    "dataType": [
                        "text"
                    ],
                    "cardinality": "atMostOne",
                    "keywords": [],
                    "index": True
                },
                {
                    "name": "members",
                    "description": "The persons that are part of this group",
                    "dataType": [
                        "Person"
                    ],
                    "cardinality": "many"
                }
            ]
        }

        w = weaviate.Client("http://localhost:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        w.schema.create_class(group_class)
        w.schema.create_class(group_class, SEMANTIC_TYPE_ACTIONS)

        connection_mock.run_rest.assert_called()
        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]
        self.assertEqual("/schema/things", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        created_class = call_args[2]
        self.assertEqual("Group", created_class["class"])
        self.assertEqual(1, len(created_class["properties"]))

        call_args, call_kwargs = call_args_list[1]
        self.assertEqual("/schema/things/Group/properties", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        created_property = call_args[2]
        self.assertEqual(["Person"], created_property["dataType"])

        call_args, call_kwargs = call_args_list[2]
        self.assertEqual("/schema/actions", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])

    def test_input(self):
        w = weaviate.Client("http://localhorst:8080")
        invalid_class = {
            "class": "Group",
            "description": "A set of persons who are associated with each other over some common properties",
            "keywords": [],
            "properties": [
                {
                    "name": "name",
                    "description": "The name under which this group is known",
                    "cardinality": "atMostOne",
                    "keywords": [],
                    "index": True
                },
                {
                    "name": "members",
                    "description": "The persons that are part of this group",
                    "dataType": [
                        "Person"
                    ],
                    "cardinality": "many"
                }
            ]
        }
        try:
            w.schema.create_class(invalid_class)
            self.fail("Expected exception")
        except SchemaValidationException:
            pass


class TestDelete(unittest.TestCase):

    def test_delete_class_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.schema.delete_class(1)
            self.fail("Expected error")
        except TypeError:
            pass
        try:
            w.schema.delete_class("a", 1)
            self.fail("Expected error")
        except TypeError:
            pass

    def test_delete_class(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        w.schema.delete_class("Poverty")
        w.schema.delete_class("Poverty", SEMANTIC_TYPE_ACTIONS)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/schema/things/Poverty", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

        call_args, call_kwargs = call_args_list[1]

        self.assertEqual("/schema/actions/Poverty", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

    def test_delete_everything(self):
        # First request get schema
        return_value_mock_get_schema = Mock()
        return_value_mock_get_schema.json.return_value = company_test_schema
        return_value_mock_get_schema.configure_mock(status_code=200)
        # Second request delete class 1
        return_value_mock_delete_class_1 = Mock()
        return_value_mock_delete_class_1.json.return_value = None
        return_value_mock_delete_class_1.configure_mock(status_code=200)
        # Third request delete class 2
        return_value_mock_delete_class_2 = Mock()
        return_value_mock_delete_class_2.json.return_value = None
        return_value_mock_delete_class_2.configure_mock(status_code=200)

        connection_mock = Mock()  # Mock calling weaviate
        #connection_mock.run_rest.return_value = [return_value_mock, return_value_mock2]
        connection_mock.run_rest.side_effect = [return_value_mock_get_schema, return_value_mock_delete_class_1, return_value_mock_delete_class_2]

        w = weaviate.Client("http://localhost:2121")
        replace_connection(w, connection_mock)

        w.schema.delete_all()

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        # Check if schema was retrieved
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/schema", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])

        # Check if class 1 was deleted
        call_args, call_kwargs = call_args_list[1]

        self.assertEqual("/schema/things/Company", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

        # Check if class 2 was deleted
        call_args, call_kwargs = call_args_list[2]

        self.assertEqual("/schema/things/Employee", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])


if __name__ == '__main__':
    unittest.main()
