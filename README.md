# Moseq-Reports-Maker
package to generate *.msq files from moseq data for consumption by moseq-reports

## Install
```
pip install git+https://github.com/tischfieldlab/moseq-reports-maker.git
```

## Usage
Begin by creating a configuration file:
```
msq-maker generate-config
```
The above command will create `msq-config.toml` in the current directory. Edit this file to with relevant information. Most critical
will be the section `[model] `. Below is an example:
```
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

If you have questions about the configuration entries for a given producer, you can lookup a description:
```
msq-maker explain-config <producer_name>
```

Finally, to generate the report, run the `make-report` command:
```
msq-maker make-report --config-file /path/to/msq-config.toml
```
