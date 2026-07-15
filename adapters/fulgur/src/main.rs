use anyhow::{Context, Result};
use fulgur::{
    config::{Margin, PageSize},
    engine::Engine,
};
use serde::{Deserialize, Serialize};
use std::{
    fs,
    io::{self, Read},
    path::PathBuf,
    time::Instant,
};

#[derive(Deserialize)]
struct Request {
    schema_version: u8,
    html: PathBuf,
    base_path: PathBuf,
    output_pdf: PathBuf,
    warmups: usize,
    iterations: usize,
}
#[derive(Serialize)]
struct Response {
    schema_version: u8,
    renderer: &'static str,
    version: &'static str,
    timing_scope: &'static str,
    samples_ms: Vec<f64>,
    output_pdf: PathBuf,
}
fn render(engine: &Engine, html: &str, output: &PathBuf) -> Result<()> {
    engine
        .render_file(html, output)
        .context("Fulgur render failed")
}
fn main() -> Result<()> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let request: Request = serde_json::from_str(&input)?;
    anyhow::ensure!(request.schema_version == 1, "unsupported schema");
    anyhow::ensure!(request.iterations > 0, "iterations must be positive");
    if let Some(parent) = request.output_pdf.parent() {
        fs::create_dir_all(parent)?
    }
    let html = fs::read_to_string(&request.html)?;
    let engine = Engine::builder()
        .page_size(PageSize::A4)
        .margin(Margin::uniform_mm(10.0))
        .base_path(request.base_path)
        .build();
    for _ in 0..request.warmups {
        render(&engine, &html, &request.output_pdf)?
    }
    let mut samples = Vec::new();
    for _ in 0..request.iterations {
        let started = Instant::now();
        render(&engine, &html, &request.output_pdf)?;
        samples.push(started.elapsed().as_secs_f64() * 1000.0)
    }
    println!(
        "{}",
        serde_json::to_string(&Response {
            schema_version: 1,
            renderer: "fulgur",
            version: env!("CARGO_PKG_VERSION"),
            timing_scope: "warm-engine",
            samples_ms: samples,
            output_pdf: request.output_pdf
        })?
    );
    Ok(())
}
