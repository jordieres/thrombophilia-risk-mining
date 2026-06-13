"""Shared abstractions for analytical experiments.

The experiment classes in this repository follow a small contract: each module
receives a preprocessed :class:`pandas.DataFrame`, performs its analysis,
stores a LaTeX representation of the results, and optionally stores an
interactive Plotly figure.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any
import plotly.graph_objects as go

class BaseExperiment(ABC):
    """Abstract baseline class defining the life-cycle contract for all experimental modules.

    Every distinct research study must inherit from this structure, implementing the required
    execution contract to ensure seamless integration into the CLI pipeline.
    """

    def __init__(self, name: str) -> None:
        """Initializes the abstract experiment parameters.

        Args:
            name (str): Unique descriptive name for the underlying analytical module.
        """
        self.name: str = name
        self.latex_table: str = ""
        self.plotly_figure: Optional[go.Figure] = None

    @abstractmethod
    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Executes the target machine learning or statistical modeling pipeline.

        Args:
            data (pd.DataFrame): Preprocessed clinical data matrix.
            config (Dict[str, Any]): Dynamic execution limits passed down from the command line.
        """
        pass

    def export_latex(self) -> str:
        """Returns the formatted production-grade LaTeX table representing results.

        Returns:
            str: Booktabs styled LaTeX tabular string.
        """
        return self.latex_table

    def save_interactive_plot(self, output_path: str) -> None:
        """Writes the optimized internal interactive Plotly figure onto disk as raw standalone HTML.

        Args:
            output_path (str): Target destination layout on the local storage file system.
        """
        if self.plotly_figure:
            self.plotly_figure.write_html(output_path)
