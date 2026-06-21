"""Recolors a previously exported UMAP coordinate table without recomputing the embedding."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import plotly.express as px
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from exp_unsupervised_clustering import UnsupervisedClusteringExperiment


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recolor an existing umap_coordinates.csv file using a JSON ruleset without recomputing UMAP."
    )
    parser.add_argument("--umap-csv", required=True, help="Path to an exported umap_coordinates.csv file.")
    parser.add_argument("--color-rules-json", required=True, help="JSON file with color rules.")
    parser.add_argument("--output-html", required=True, help="Path to the recolored Plotly HTML output.")
    parser.add_argument(
        "--title",
        default="Recolored UMAP Projection",
        help="Optional chart title for the recolored projection.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    umap_csv = Path(args.umap_csv)
    color_rules_json = Path(args.color_rules_json)
    output_html = Path(args.output_html)

    export_df = pd.read_csv(umap_csv)
    required_columns = {"umap_dimension_1", "umap_dimension_2", "cluster"}
    missing_columns = sorted(required_columns - set(export_df.columns))
    if missing_columns:
        raise ValueError(f"UMAP coordinate file is missing required columns: {missing_columns}")

    experiment = UnsupervisedClusteringExperiment()
    export_df = export_df.copy()
    export_df["color_group"] = experiment._build_color_groups(  # noqa: SLF001
        export_df=export_df,
        color_rules_path=color_rules_json,
    )

    figure = px.scatter(
        export_df,
        x="umap_dimension_1",
        y="umap_dimension_2",
        color="color_group",
        title=str(args.title),
        hover_data={
            "cluster": True,
            "color_group": True,
        },
    )

    output_html.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(str(output_html), include_plotlyjs="cdn")

    recolored_csv = output_html.with_name(output_html.stem + "_with_colors.csv")
    export_df.to_csv(recolored_csv, index=False)

    print(f"Recolored HTML written to {output_html}")
    print(f"Recolored coordinate table written to {recolored_csv}")


if __name__ == "__main__":
    main()
