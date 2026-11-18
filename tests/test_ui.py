from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_pages_and_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("AML_DB_PATH", str(tmp_path / "ui.sqlite3"))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15)
    app.run()
    assert not app.exception and app.main.title[0].value == "Memory Browser"
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert any("PostgreSQL" in text for text in app.dataframe[0].value["Content"])
    entries = app.dataframe[0].value.set_index("Content")
    assert entries.loc["项目使用 SQLite 数据库", "Status"] == "superseded"

    count = len(app.dataframe[0].value)
    app.sidebar.button[0].click().run()
    assert len(app.dataframe[0].value) == count

    app.sidebar.radio[0].set_value("Memory Timeline").run()
    assert not app.exception and app.get("plotly_chart")
    assert "SQLite" in " ".join(app.dataframe[0].value["Content"])
    app.date_input[0].set_value(date(2025, 6, 1)).run()
    assert any("PostgreSQL" in text for text in app.dataframe[0].value["Content"])
    assert "项目使用 SQLite 数据库" not in list(app.dataframe[0].value["Content"])

    app.sidebar.radio[0].set_value("Retrieval Lab").run()
    assert not app.exception
    assert {header.value for header in app.subheader} >= {"Recent", "BM25", "Vector", "Hybrid"}

    app.sidebar.radio[0].set_value("Benchmark Dashboard").run()
    assert not app.exception and len(app.get("plotly_chart")) == 3
    app.main.selectbox[0].set_value("Unanswerable").run()
    assert not app.exception and len(app.get("plotly_chart")) == 2
