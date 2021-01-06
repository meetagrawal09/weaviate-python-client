import json
from typing import Union


class Explore:
    """
    Explore class used to interact with objects from weaviate.
    """

    def __init__(self, content: dict):
        """
        Initialize an Explore class instance.

        Parameters
        ----------
        content : dict
            The content of the `explore` clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        TypeError
            If 'content'  has key "certainty" but the value is not float.
        """

        if not isinstance(content, dict):
            raise TypeError(f"Explore filter is expected to be type dict but was {type(content)}")

        self.concepts = _check_concept(content)
        self.certainty = None
        self.move_to = None
        self.move_away_from = None

        if "certainty" in content:
            if not isinstance(content["certainty"], float):
                raise TypeError(f"certainty is expected to be a float but was \
                                {type(content['certainty'])}")

            self.certainty = content["certainty"]

        if "moveTo" in content:
            self.move_to = _check_direction_clause(content["moveTo"])

        if "moveAwayFrom" in content:
            self.move_away_from = _check_direction_clause(content["moveAwayFrom"])


    def __str__(self):
        explore = f'{{concepts: {json.dumps(self.concepts)} '
        if self.certainty is not None:
            explore += f'certainty: {str(self.certainty)} '
        if self.move_to is not None:
            explore += f'moveTo:{{concepts: {json.dumps(self.move_to["concepts"])} \
                        force: {self.move_to["force"]}}} '
        if self.move_away_from is not None:
            explore += f'moveAwayFrom:{{concepts: {json.dumps(self.move_away_from["concepts"])} \
                        force: {self.move_away_from["force"]}}} '
        return explore + '}'


class WhereFilter:
    """
    WhereFilter class used to interact with objects from weaviate.
    """

    def __init__(self, content: dict):
        """
        Initialize a WhereFilter class instance.

        Parameters
        ----------
        content : dict
            The content of the `where` filter clause.

        Raises
        ------
        TypeError
            If 'content' is not of type dict.
        ValueError
            If a mandatory key is missing in the filter content.
        """

        if not isinstance(content, dict):
            raise TypeError(f"WhereFilter is expected to be type dict but was {type(content)}")

        if "path" in content:
            self.is_filter = True
            self._parse_filter(content)
        elif "operands" in content:
            self.is_filter = False
            self._parse_operator(content)
        else:
            raise ValueError("Filter is missing required fileds: ", content)

    def _parse_filter(self, content: dict) -> None:
        """
        Set filter fields for the WhereFilter.

        Parameters
        ----------
        content : dict
            The content of the `where` filter clause.

        Raises
        ------
        ValueError
            If 'content' is missing required fields.
        """

        if "operator" not in content:
            raise ValueError("Filter is missing required fileds: ", content)

        self.path = json.dumps(content["path"])
        self.operator = content["operator"]
        self.value_type = _find_value_type(content)
        self.value = content[self.value_type]

    def _parse_operator(self, content: dict) -> None:
        """
        Set operator fields for the WhereFilter.

        Parameters
        ----------
        content : dict
            The content of the `where` filter clause.

        Raises
        ------
        ValueError
            If 'content' is missing required fields.
        """

        if "operator" not in content:
            raise ValueError("Filter is missing required fileds: ", content)

        self.operator = content["operator"]
        self.operands = []
        for operand in content["operands"]:
            self.operands.append(WhereFilter(operand))

    def __str__(self):
        if self.is_filter:
            gql = f'{{path: {self.path} operator: {self.operator} {self.value_type}: '
            if self.value_type in ["valueInt", "valueNumber"]:
                gql += f'{self.value}}}'
            elif self.value_type == "valueBoolean":
                bool_value = str(self.value).lower()
                gql += f'{bool_value}}}'
            elif self.value_type == "valueGeoRange":
                geo_value = json.dumps(self.value)
                gql += f'{geo_value}}}'
            else:
                gql += f'"{self.value}"}}'
            return gql

        operands_str = []
        for operand in self.operands:
            operands_str.append(str(operand))
        operands = ", ".join(operands_str)
        return f'{{operator: {self.operator} operands: [{operands}]}}'


def _check_direction_clause(direction: dict) -> dict:
    """
    Validate the direction sub clause.

    Parameters
    ----------
    direction : dict
        A sub clause of the Explore filter.

    Returns
    -------
    dict
        Returns back the original 'direction' if it passed the validation.

    Raises
    ------
    TypeError
        If 'direction' is not a dict.
    TypeError
        If the value of the "force" key is not float.
    ValueError
        If no "force" key in the 'direction'.
    """

    if not isinstance(direction, dict):
        raise TypeError(f"move clause should be dict but was {type(direction)}")
    _check_concept(direction)
    if not "force" in direction:
        raise ValueError("move clause needs to state a force")
    if not isinstance(direction["force"], float):
        raise TypeError(f"force should be float but was {type(direction['force'])}")
    return direction


def _check_concept(content: dict) -> Union[list, str]:
    """
    Validate the concept sub clause.

    Parameters
    ----------
    content : dict
        An Explore (sub) clause to chack for 'concepts'.

    Returns
    -------
    list or str
        Concept/s of the (sub) clause.

    Raises
    ------
    ValueError
        If no "concepts" key in the 'content' dict.
    TypeError
        If the value of the  "concepts" is of wrong type.
    """

    if "concepts" not in content:
        raise ValueError("No concepts in content")

    if not isinstance(content["concepts"], (list, str)):
        raise TypeError(f"Concepts must be of type list or str not {type(content['concepts'])}")
    return content["concepts"]


def _find_value_type(content: dict) -> str:
    """
    Find the correct type of the content.

    Parameters
    ----------
    content : dict
        The content for which to find the appropriate data type.

    Returns
    -------
    str
        The correct data type.

    Raises
    ------
    ValueError
        If missing required fields.
    """

    if "valueString" in content:
        return "valueString"
    if "valueText" in content:
        return "valueText"
    if "valueInt" in content:
        return "valueInt"
    if "valueNumber" in content:
        return "valueNumber"
    if "valueDate" in content:
        return "valueDate"
    if "valueBoolean" in content:
        return "valueBoolean"
    if "valueGeoRange" in content:
        return "valueGeoRange"
    raise ValueError("Filter is missing required fileds: ", content)
