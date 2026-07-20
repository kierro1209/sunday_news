"""Render the edition as a newspaper-styled HTML email and send via Resend."""

from __future__ import annotations

import html
import re

import httpx

from .config import Config


def _md_to_html(text: str) -> str:
    """Tiny markdown subset (links, bold, italics, paragraphs) safe for email."""
    out = html.escape(text or "")
    out = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2" style="color:#8a6d3b;">\1</a>',
        out,
    )
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    paragraphs = [p.strip().replace("\n", "<br/>") for p in out.split("\n\n") if p.strip()]
    return "".join(f'<p style="margin:0 0 10px;">{p}</p>' for p in paragraphs)


def _meta_line(article: dict) -> str:
    """Byline row: authors (linked when known), publication, date, source link."""
    bits = []
    authors = article.get("authors") or []
    if authors:
        rendered = []
        for author in authors:
            name = html.escape(author.get("name", ""))
            if author.get("url"):
                rendered.append(f'<a href="{html.escape(author["url"])}" style="color:#666;">{name}</a>')
            else:
                rendered.append(name)
        bits.append("By " + ", ".join(rendered))
    elif article.get("byline"):
        bits.append(html.escape(article["byline"]))
    if article.get("publication"):
        bits.append(html.escape(article["publication"]))
    if article.get("published"):
        bits.append(html.escape(article["published"]))
    if article.get("url"):
        bits.append(f'<a href="{html.escape(article["url"])}" style="color:#8a6d3b;">original source</a>')
    return " &middot; ".join(bits)


def _article_html(article: dict) -> str:
    headline = html.escape(article.get("headline", ""))
    if article.get("url"):
        headline = (
            f'<a href="{html.escape(article["url"])}" '
            f'style="color:#1a1a1a;text-decoration:underline;">{headline}</a>'
        )
    difficulty = article.get("difficulty", "")
    diff_badge = (
        f'<span style="font-size:11px;color:#8a6d3b;border:1px solid #c9b98a;'
        f'padding:0 5px;margin-left:6px;">{html.escape(difficulty)}</span>'
        if difficulty
        else ""
    )
    return f"""
    <div style="margin:0 0 22px;">
      <h3 style="font-family:Georgia,serif;font-size:19px;margin:0 0 4px;line-height:1.25;">
        {headline}{diff_badge}
      </h3>
      <div style="font-size:12px;color:#666;font-style:italic;margin:0 0 8px;">
        {_meta_line(article)}
      </div>
      <div style="font-size:14px;line-height:1.55;color:#222;">
        {_md_to_html(article.get('body', ''))}
      </div>
    </div>"""


def render_email_html(edition: dict, web_app_url: str) -> str:
    sections_html = ""
    for section in edition.get("sections", []):
        articles = "".join(_article_html(a) for a in section.get("articles", []))
        sections_html += f"""
        <div style="border-top:2px solid #1a1a1a;margin-top:18px;padding-top:10px;">
          <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#8a6d3b;">
            {html.escape(section.get('kicker', ''))}
          </div>
          <h2 style="font-family:Georgia,serif;font-size:24px;margin:2px 0 14px;">
            {html.escape(section.get('heading', ''))}
          </h2>
          {articles}
        </div>"""

    web_link = (
        f'<p style="text-align:center;font-size:13px;">'
        f'<a href="{html.escape(web_app_url)}" style="color:#8a6d3b;">'
        f"Read online — take notes, rate articles, export PDF</a></p>"
        if web_app_url
        else ""
    )

    label = "SUNDAY WEEKLY EDITION" if edition["kind"] == "weekly" else "DAILY EDITION"
    return f"""<!DOCTYPE html>
<html><body style="margin:0;background:#f4f1e8;padding:20px 0;">
  <div style="max-width:680px;margin:0 auto;background:#fdfbf4;border:1px solid #d8d2bf;padding:28px 32px;">
    <div style="text-align:center;border-bottom:3px double #1a1a1a;padding-bottom:12px;">
      <div style="font-size:11px;letter-spacing:2px;color:#666;">{label} — {html.escape(edition['date'])} — {html.escape(edition.get('volume', ''))}</div>
      <h1 style="font-family:Georgia,serif;font-size:40px;margin:6px 0 2px;">The Magnolia Times</h1>
      <div style="font-size:12px;font-style:italic;color:#666;">{html.escape(edition.get('motto', ''))}</div>
    </div>
    {sections_html}
    <div style="border-top:3px double #1a1a1a;margin-top:24px;padding-top:12px;">
      {web_link}
      <p style="text-align:center;font-size:11px;color:#999;">Curated for you by the Magnolia Times editor agent.</p>
    </div>
  </div>
</body></html>"""


def send_edition(cfg: Config, edition: dict) -> None:
    kind_label = "Sunday Weekly" if edition["kind"] == "weekly" else "Daily"
    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {cfg.resend_api_key}"},
        json={
            "from": cfg.email_from,
            "to": [cfg.email_to],
            "subject": f"The Magnolia Times — {kind_label} — {edition['date']}",
            "html": render_email_html(edition, cfg.web_app_url),
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    print(f"  [email] sent to {cfg.email_to} (id: {resp.json().get('id')})")
