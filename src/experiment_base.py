"""Shared abstractions for analytical experiments.

The experiment classes in this repository follow a small contract: each module
receives a preprocessed :class:`pandas.DataFrame`, performs its analysis,
stores a LaTeX representation of the results, and optionally stores an
interactive Plotly figure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from os import PathLike
from typing import Final

import pandas as pd
from plotly.basedatatypes import BaseFigure


class BaseExperiment(ABC):
    """Abstract base class for thrombophilia analytical experiments.

    Attributes:
        name: Human-readable experiment name used in CLI output and file names.
        latex_table: LaTeX representation of the latest experiment results.
        plotly_figure: Optional interactive figure created during execution.
    """

    EMPTY_LATEX: Final[str] = ""

    def __init__(self, name: str) -> None:
        """Initialize the common experiment state.

        Args:
            name: Descriptive name shown in the CLI and output artifacts.
        """
        self.name: str = name
        self.latex_table: str = self.EMPTY_LATEX
        self.plotly_figure: BaseFigure | None = None

    @abstractmethod
    def run(self, data: pd.DataFrame) -> None:
        """Execute the experiment and populate output artifacts.

        Args:
            data: Preprocessed clinical dataset produced by the shared pipeline.
        """

    def export_latex(self) -> str:
        """Return the LaTeX representation produced by the last run.

        Returns:
            LaTeX table content formatted for inclusion in reports.
        """
        return self.latex_table

    def save_interactive_plot(self, output_path: str | PathLike[str]) -> None:
        """Persist the interactive Plotly figure as a standalone HTML file.

        Args:
            output_path: Destination path for the generated HTML artifact.
        """
        if self.plotly_figure is not None:
            self.plotly_figure.write_html(str(output_path))
