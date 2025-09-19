from typing import Any, Dict

import pandas as pd
from pydantic import BaseModel


def standardize_dataframe(
    cls: type[BaseModel], df: pd.DataFrame, drops: list[str] | None = None, by_alias: bool = False, **kwargs
) -> pd.DataFrame:
    drops = drops or []
    temp = df.copy()
    temp.drop(columns=drops, errors="ignore", inplace=True)
    for key, value in kwargs.items():
        temp[key] = value

    try:
        output = temp.drop_duplicates()
    except TypeError:
        output = temp

    return output.reset_index(drop=True).apply(
        lambda row: cls.model_validate(**row.to_dict()).model_dump(mode="python", by_alias=by_alias),
        axis=1,
        result_type="expand",
    )


def convert_dto_obj_on_serialize(
    *,
    obj: BaseModel,
    id_field: str,
    id_field_attr_name: str,
    target_field: str,
    expected_output_field_type: type,
    expected_intput_field_type: type,
) -> Dict[str, Any]:
    data = obj.model_dump()
    field = getattr(obj, id_field)
    data[target_field] = getattr(field, id_field_attr_name) if isinstance(field, expected_intput_field_type) else field
    if not isinstance(data[target_field], expected_output_field_type):
        raise TypeError(
            f"The output type of the field {id_field} was not expected {expected_output_field_type.__name__}"
        )

    data.pop(id_field)
    return data
