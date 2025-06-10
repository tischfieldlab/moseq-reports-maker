import logging
import os
import click

from msq_maker.config import MoseqReportsConfig
from msq_maker.model import get_model_config
from msq_maker.msq import MSQ
from msq_maker.util import setup_logging

from .producers import PluginRegistry


@click.group()
@click.version_option()
def cli():
    pass  # pylint: disable=unnecessary-pass


@cli.command(name="generate-config", short_help="Generates a configuration file that holds editable options for producer parameters.")
@click.option("--name", type=str, default="moseq-reports", help="Name of the generated report.")
@click.option("--model", type=click.Path(), default=None, help="Path to a moseq model.")
@click.option("--index", type=click.Path(), default=None, help="Path to a moseq index.")
@click.option("--manifest", type=click.Path(), default=None, help="Path to a manifest.")
@click.option("--output-file", "-o", type=click.Path(), default="msq-config.toml", help="Path where configuration should be saved.")
def generate_config(name, model, index, manifest, output_file: str):
    """Generates a configuration file for creating a moseq-reports msq file."""
    setup_logging()
    output_file = os.path.abspath(output_file)

    config = MoseqReportsConfig()

    # set MSQ configuration
    output_dir = os.path.dirname(output_file)
    config.msq.name = name
    config.msq.out_dir = output_dir
    config.msq.tmp_dir = os.path.join(output_dir, "tmp")

    # set model configuration
    config.model = get_model_config(model, index, manifest)

    # finally, write the config file
    config.write_config(output_file)
    logging.info(f'Successfully generated config file at "{output_file}".')


@cli.command(name="list-producers", short_help="Lists all available producers.")
def list_producers():
    setup_logging()
    if len(PluginRegistry.registry) == 0:
        logging.warning("No producers found.")
        return

    print("Available producers:")
    for producer in PluginRegistry.registry.keys():
        print(f" - {producer}")


@cli.command(name="explain-config", short_help="Generates a report using the specified producer.")
@click.argument("producer", type=str, required=True)
def explain_config(producer: str):
    setup_logging()
    producer_class = PluginRegistry.registry.get(producer)
    if producer_class is None:
        logging.warning(f"Producer {producer} not found.")
        return

    # Assuming the producer has a method to explain its configuration
    explanation = producer_class.get_args_type().document()
    print(f"Configuration for {producer}:")
    print(explanation)


@cli.command(name="make-report", short_help="Generates a report using the specified producer.")
@click.option("--config-file", "-c", type=click.Path(exists=True), default="msq-config.toml", help="Path to the configuration file.")
def make_report(config_file: str):
    config = MoseqReportsConfig.read_config(config_file)
    msq = MSQ(config.msq)
    msq.write_unstructured("msq_config.json", config.to_dict())
    msq.manifest["msq_config"] = "msq_config.json"

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
