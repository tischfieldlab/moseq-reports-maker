import logging
import os
import traceback
import click

from msq_maker.msq import MSQ
from msq_maker.util import setup_logging

from .producers import MoseqReportsConfig, PluginRegistry


@click.group()
@click.version_option()
def cli():
    pass  # pylint: disable=unnecessary-pass


@cli.command(name="generate-config", short_help="Generates a configuration file that holds editable options for producer parameters.")
@click.option("--output-file", "-o", type=click.Path(), default="msq-config.toml", help="Path where configuration should be saved.")
def generate_config(output_file: str):
    setup_logging()
    output_file = os.path.abspath(output_file)
    MoseqReportsConfig().write_config(output_file)
    logging.info(f'Successfully generated config file at "{output_file}".')


@cli.command(name="list-producers", short_help="Lists all available producers.")
def list_producers():
    setup_logging()
    if len(PluginRegistry.registry) == 0:
        logging.info("No producers found.")
        return

    logging.info("Available producers:")
    for producer in PluginRegistry.registry.keys():
        logging.info(f" - {producer}")


@cli.command(name="explain-config", short_help="Generates a report using the specified producer.")
@click.argument("producer", type=str, required=True)
def explain_config(producer: str):
    setup_logging()
    producer_class = PluginRegistry.registry.get(producer)
    if producer_class is None:
        logging.info(f"Producer {producer} not found.")
        return

    # Assuming the producer has a method to explain its configuration
    explanation = producer_class.get_args_type().document()
    logging.info(f"Configuration for {producer}:")
    logging.info(explanation)


@cli.command(name="make-report", short_help="Generates a report using the specified producer.")
@click.option("--config-file", "-c", type=click.Path(exists=True), default="msq-config.toml", help="Path to the configuration file.")
def make_report(config_file: str):
    config = MoseqReportsConfig.read_config(config_file)
    msq = MSQ(config.msq)

    setup_logging(os.path.join(config.msq.out_dir, "moseq_reports.log"))

    for producer_name, producer_config in config.producers.items():
        producer_class = PluginRegistry.registry.get(producer_name)

        if producer_class is None:
            logging.warning(f"Producer {producer_name} not found.")
            continue

        if producer_config.enabled is False:
            logging.info(f"Skipping {producer_name} as it is disabled in the config.")
            continue

        logging.info(f"Running {producer_name}...")
        try:
            producer_instance = producer_class(config)
            producer_instance.run(msq)
        except:
            logging.exception(f"Error generating {producer_name}, but continuing onward.")
        logging.info(f"Finished running {producer_name}.")

    logging.info("Bundling report...")
    msq.bundle()
    logging.info(f"Report generated at {msq.report_path}.")
    logging.info("Report generation complete.")


if __name__ == "__main__":
    cli()
