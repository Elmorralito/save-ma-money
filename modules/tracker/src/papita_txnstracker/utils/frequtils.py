"""Time frequency handler module"""

from typing import Any, Union

import pandas as pd
from heka.utils.modelutils import parse_dates
from pandas.tseries.offsets import BaseOffset
from typing_extensions import Self


class FrequencyHandler:
    """
    Pandas frequency comparison approach class.

    Attributes:
        SAMPLE_PERIODS (int): Number of sample periods for frequency comparison.
    """

    SAMPLE_PERIODS: int = 15

    def __init__(
        self, freq: Union[str, Self, BaseOffset], ref_dt: Any = None, sample_periods: int | float | None = None
    ) -> None:
        """
        Initialize the FrequencyHandler instance.

        Args:
            freq (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.
            ref_dt (pd.Timestamp, optional): Reference timestamp. Defaults to current timestamp.
        """
        if isinstance(freq, FrequencyHandler):
            self._freq = freq.freq
            self._offset = freq.offset
            self._ref_dt = ref_dt or freq.ref_dt
            self._sample_dt = freq.sample_dt
            return

        self._offset = pd.tseries.frequencies.to_offset(freq)
        self._freq = freq
        self._ref_dt = parse_dates(ref_dt) or pd.Timestamp.now()
        self._sample_periods = int(sample_periods) if isinstance(sample_periods, (int, float)) else self.SAMPLE_PERIODS
        self._sample_dt = pd.period_range(self._ref_dt, periods=self._sample_periods, freq=self._freq).max()
        self._sample_dt = self._sample_dt.to_timestamp()

    @property
    def freq(self) -> str:
        """
        Return the raw frequency string.

        Returns:
            str: Frequency string.
        """
        return self._freq.freqstr if isinstance(self._freq, BaseOffset) else self._freq

    @property
    def offset(self) -> pd.DateOffset:
        """
        Return the offset built from the frequency.

        Returns:
            pd.DateOffset: Offset corresponding to the frequency.
        """
        return self._offset

    @property
    def ref_dt(self) -> pd.Timestamp:
        """
        Return the initial/reference timestamp.

        Returns:
            pd.Timestamp: Reference timestamp.
        """
        return self._ref_dt

    @property
    def sample_dt(self) -> pd.Timestamp:
        """
        Return the sample timestamp used for comparing among frequencies.

        Returns:
            pd.Timestamp: Sample timestamp.
        """
        return self._sample_dt

    @property
    def sample_periods(self) -> int:
        """
        Return the number of sample periods used for comparing among frequencies.

        Returns:
            int: Sample periods.
        """
        return self._sample_periods

    @property
    def unit(self) -> str:
        """
        Return the base unit of the provided frequency.

        Returns:
            str: Base unit of the frequency.
        """
        return self.offset.base.freqstr

    def _check_freq(self, other) -> "FrequencyHandler":
        """
        Check and convert the input to a FrequencyHandler instance.

        Args:
            other (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.

        Returns:
            FrequencyHandler: FrequencyHandler instance corresponding to the input.

        Raises:
            TypeError: If the input type is not supported.
        """
        if isinstance(other, (str, BaseOffset)):
            return FrequencyHandler(other, ref_dt=self._ref_dt)

        if isinstance(other, FrequencyHandler):
            return other

        raise TypeError(f"type '{type(other)}' not supported.")

    def __compare(self, other, comparator) -> bool:
        """
        Compare the frequency with another frequency using the specified comparator.

        Args:
            other (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.
            comparator (str): Comparator method name.

        Returns:
            bool: Result of the comparison.
        """
        other_freq = self._check_freq(other)
        return getattr(self._sample_dt, comparator)(other_freq.sample_dt)

    def __eq__(self, other: Union[str, Self, BaseOffset]) -> bool:
        """
        Check if the frequency is equal to another frequency.

        Args:
            other (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.

        Returns:
            bool: True if equal, False otherwise.
        """
        return self.__compare(other, "__eq__")

    def __ge__(self, other: Union[str, Self, BaseOffset]) -> bool:
        """
        Check if the frequency is greater than or equal to another frequency.

        Args:
            other (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.

        Returns:
            bool: True if greater than or equal, False otherwise.
        """
        return self.__compare(other, "__ge__")

    def __gt__(self, other: Union[str, Self, BaseOffset]) -> bool:
        """
        Check if the frequency is greater than another frequency.

        Args:
            other (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.

        Returns:
            bool: True if greater, False otherwise.
        """
        return self.__compare(other, "__gt__")

    def __le__(self, other: Union[str, Self, BaseOffset]) -> bool:
        """
        Check if the frequency is less than or equal to another frequency.

        Args:
            other (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.

        Returns:
            bool: True if less than or equal, False otherwise.
        """
        return self.__compare(other, "__le__")

    def __lt__(self, other: Union[str, Self, BaseOffset]) -> bool:
        """
        Check if the frequency is less than another frequency.

        Args:
            other (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.

        Returns:
            bool: True if less, False otherwise.
        """
        return self.__compare(other, "__lt__")

    def __ne__(self, other: Union[str, Self, BaseOffset]) -> bool:
        """
        Check if the frequency is not equal to another frequency.

        Args:
            other (Union[str, FrequencyHandler]): Frequency string or another FrequencyHandler instance.

        Returns:
            bool: True if not equal, False otherwise.
        """
        return self.__compare(other, "__ne__")

    def __str__(self):
        """
        Return the string representation of the frequency.

        Returns:
            str: Frequency string.
        """
        return self.freq

    def __repr__(self) -> str:
        """
        Return the detailed string representation of the FrequencyHandler instance.

        Returns:
            str: Detailed string representation.
        """
        return f"{self.__class__.__name__}(freq='{str(self)}')"

    def __lshift__(self, other: Union[str, Self, BaseOffset]) -> int:
        freq = FrequencyHandler(other, ref_dt=self.ref_dt, sample_periods=self.sample_periods)
        if freq > self:
            raise ValueError(f"The frequency '{other}' is greater than '{self}'.")

        if freq == self:
            return 1

        range_ = pd.date_range(start=self.ref_dt, end=self.sample_dt, freq=freq.offset, inclusive=True)
        return len(range_) - 1
