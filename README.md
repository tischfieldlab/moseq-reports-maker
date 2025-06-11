# Moseq-Reports-Maker
package to generate *.msq files from moseq data for consumption by moseq-reports

## Install
`moseq-reports-maker` can be installed into a `moseq2-app` environment, or you could make your own virtual environment:
```sh
conda create -n moseq-reports-maker python=3.7
conda activate moseq-reports-maker
```

Please ensure the following dependencies are installed:
```sh
conda install -c conda-forge ffmpeg=4.2.0
pip install git+https://github.com/dattalab/moseq2-viz.git
pip install git+https://github.com/tischfieldlab/moseq-spinogram.git
pip install git+https://github.com/tischfieldlab/moseq-syllable-clips.git
```

Then install this package:
```sh
pip install git+https://github.com/tischfieldlab/moseq-reports-maker.git
```

## Usage
Begin by creating a configuration file:
```sh
msq-maker make-config
```

The above command will create `msq-config.toml` in the current directory. Edit this file to with relevant information. Most critical
will be the section `[model] `. Below is an example:
```ini
[model]
index = "/path/to/moseq2-index.yaml"
model = "/path/to/moseq-model.p"
max_syl = 35
sort = true
count = "usage"
groups = ["WT", "Mutant"]
raw_data_path = "/path/to/raw/data"
manifest_path = ""
manifest_uuid_column = "uuid"
manifest_session_id_column = "session_id"
```

To avoid having to manually edit the configuration file, you may provide some additional arguments to the `make-config` command:
```sh
msq-maker make-config --name name-of-the-generated-report --model /path/to/a/model.p --index /path/to/a/index.yaml --manifest /path/to/a/manifest.csv
```

If you have questions about the configuration entries for a given producer, you can lookup a description:
```sh
msq-maker explain-config <producer_name>
```

To get a list of available producers, run the command:
```sh
msq-maker list-producers
```
will generate output something like:
```txt
Available producers:
 - behavioral_distance
 - crowd_movies
 - groups
 - label_map
 - sample_manifest
 - scalars
 - spinograms
 - syllable_clips
 - transitions
 - usage
```

Finally, to generate the report, run the `make-report` command:
```sh
msq-maker make-report --config-file /path/to/msq-config.toml
```
