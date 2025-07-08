import logging
from msq_maker.util import add_file_logging, setup_logging
setup_logging()

import msq_maker.monkey_patch  # noqa: F401, to ensure monkey patching is applied


import os
from typing import List
import click

from msq_maker.core import BaseOptionalProducerArgs, MSQConfig, ModelConfig, MoseqReportsConfig, PluginRegistry, MSQ
from msq_maker.model import get_model_config

import msq_maker.producers # noqa: F401, to ensure producers are registered


@click.group()
@click.version_option()
def cli():
    pass  # pylint: disable=unnecessary-pass


@cli.command(name="make-config", short_help="Generates a configuration file that holds editable options for producer parameters.")
@click.option("--name", type=str, default="moseq-reports", help="Name of the generated report.")
@click.option("--model", type=click.Path(exists=True, dir_okay=False), default=None, help="Path to a moseq model.")
@click.option("--index", type=click.Path(exists=True, dir_okay=False), default=None, help="Path to a moseq index.")
@click.option("--raw-data", type=click.Path(exists=True, file_okay=False), default=None, help="Path to the directory containing your raw moseq session data.")
@click.option("--manifest", type=click.Path(exists=True, dir_okay=False), default=None, help="Path to a manifest.")
@click.option("--manifest-uuid-col", type=str, default="UUID", help="Column name in the manifest file that contains the UUIDs of the extractions.")
@click.option("--manifest-session-id-col", type=str, default="Session_ID", help="Column name in the manifest file that contains the session IDs (i.e. `session_*`).")
@click.option("--group", "-g", type=str, multiple=True, help="Groups to include, if not specified, all groups will be included.")
@click.option("--output-file", "-o", type=click.Path(), default="msq-config.toml", help="Path where configuration should be saved.")
@click.option("--disable-all", type=bool, is_flag=True, help="Disable all producers.")
@click.option("--enable", type=click.Choice(PluginRegistry.registered_optional()), multiple=True, help="Enable specific producers by name. Use this to include only the producers you want in the report.")
@click.option("--disable", type=click.Choice(PluginRegistry.registered_optional()), multiple=True, help="Disable specific producers by name. Use this to skip producers you do not want in the report.")
def make_config(name: str, model: str, index: str, raw_data: str, manifest: str, manifest_uuid_col: str, manifest_session_id_col: str, group: List[str], output_file: str, disable_all: bool, enable: List[str], disable: List[str]):
    """Generates a configuration file for creating a moseq-reports msq file."""
    output_file = os.path.abspath(output_file)
    args = locals()

    config = MoseqReportsConfig()

    # set MSQ configuration
    output_dir = os.path.dirname(output_file)
    config.msq.name = name
    config.msq.out_dir = output_dir
    config.msq.tmp_dir = os.path.join(output_dir, "tmp")

    # set model configuration
    config.model = get_model_config(
        model_file=model, 
        index_file=index,
        manifest_file=manifest,
        manifest_uuid_col=manifest_uuid_col,
        manifest_session_id_col=manifest_session_id_col,
        raw_dir=raw_data,
        groups=group
    )

    if disable_all:
        for producer_name, producer_config in config.producers.items():
            if isinstance(producer_config, BaseOptionalProducerArgs):
                producer_config.enabled = False
                logging.info(f"Disabled producer: {producer_name}")

    for disabled_producer in disable:
        if disabled_producer in config.producers:
            producer_config = config.producers[disabled_producer]
            if isinstance(producer_config, BaseOptionalProducerArgs):
                producer_config.enabled = False
                logging.info(f"Disabled producer: {disabled_producer}")
            else:
                logging.warning(f"Producer {disabled_producer} is not optional and cannot be disabled.")
        else:
            logging.warning(f"Producer {disabled_producer} not found in the configuration.")

    for enabled_producer in enable:
        if enabled_producer in config.producers:
            producer_config = config.producers[enabled_producer]
            if isinstance(producer_config, BaseOptionalProducerArgs):
                producer_config.enabled = True
                logging.info(f"Enabled producer: {enabled_producer}")
            else:
                logging.warning(f"Producer {enabled_producer} is not optional and will always be enabled.")
        else:
            logging.warning(f"Producer {enabled_producer} not found in the configuration.")

    # finally, write the config file
    config.write_config(output_file)
    logging.info(f'Successfully generated config file at "{output_file}".')


@cli.command(name="list-producers", short_help="Lists all available producers.")
def list_producers():
    if len(PluginRegistry) == 0:
        logging.warning("No producers found.")
        return

    print("Available producers:")
    for producer_name in PluginRegistry.registered():
        producer = PluginRegistry.get(producer_name)

        print(f" - {producer_name} ({'Optional' if producer.is_optional() else 'Required'})")


@cli.command(name="explain-config", short_help="Generates a report using the specified producer.")
@click.argument("producer", type=str, required=True)
def explain_config(producer: str):

    if producer == "model":
        explanation = ModelConfig.document(name="Model")
    elif producer == "msq":
        explanation = MSQConfig.document(name="MSQ")
    else:
        producer_class = PluginRegistry.get(producer)
        if producer_class is None:
            logging.warning(f"Producer {producer} not found.")
            return

        explanation = producer_class.get_args_type().document(name=producer)

    print(explanation)


@cli.command(name="make-report", short_help="Generates a report using the specified producer.")
@click.option("--config-file", "-c", type=click.Path(exists=True), default="msq-config.toml", required=True, help="Path to the configuration file.")
def make_report(config_file: str):
    config = MoseqReportsConfig.read_config(config_file)
    msq = MSQ(config.msq)
    msq.prepare()
    msq.write_unstructured("msq_config.json", config.to_dict())
    msq.manifest["msq_config"] = "msq_config.json"

    add_file_logging(os.path.join(config.msq.out_dir, f"{config.msq.name}.msq-maker.log"))

    errors = []
    for producer_name, producer_config in config.producers.items():
        producer_class = PluginRegistry.get(producer_name)

        if producer_class is None:
            logging.warning(f"Producer \"{producer_name}\" not found.")
            continue

        if isinstance(producer_config, BaseOptionalProducerArgs) and producer_config.enabled is False:
            logging.info(f"Skipping producer \"{producer_name}\" since it is disabled in the config.")
            continue

        logging.info(f"Running producer \"{producer_name}\"...")
        try:
            producer_instance = producer_class(config)
            producer_instance.run(msq)
        except:
            errors.append(producer_name)
            logging.exception(f"Error generating {producer_name}, but continuing onward.")
        logging.info(f"Finished running {producer_name}.")

    logging.info("Bundling report...")
    msq.bundle()
    logging.info(f"Report generated at {msq.report_path}.")
    msq.post()
    logging.info("Report generation complete.")

    if len(errors) > 0:
        logging.warning("Errors occurred in the following producers during report generation:")
        for error in errors:
            logging.warning(f" - {error}")


if __name__ == "__main__":
    cli()
