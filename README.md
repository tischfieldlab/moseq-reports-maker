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


If you have questions about the configuration entries for a given producer, you can lookup a description:
```sh
msq-maker explain-config <producer_name>
```
This will list documentation for the producer and it's arguments. Here is an example for the `crowd_movies` producer
```sh
msq-maker explain-config crowd_movies
```
```
About the configuration for `crowd_movies`

    Configuration for the `crowd_movies` producer, implemented by the moseq2-viz package.

This producer is optional. You can enable or disable it in the configuration file.

Configuration Items:
  - enabled (bool): Enable or disable this producer. (default: True)
  - raw_size (Union[Literal['auto'], Tuple[int, int]]): Size of the raw depth movie. If auto, will be estimated from the extraction metadata. (default: auto)
  - max_examples (int): Maximum number of examples to show per syllable. (default: 40)
  - processes (Union[int, Literal['auto']]): Number of processes to use for creating movies. If "auto", will use the number of available CPU cores (taking into account CPU affinity on systems that support it). (default: auto)
  - gaussfilter_space (Tuple[float, float]): x sigma and y sigma for Gaussian spatial filter to apply to data. (default: (0, 0))
  - medfilter_space (int): kernel size for median spatial filter. (default: 0)
  - min_height (int): Minimum height for scaling videos. (default: 5)
  - max_height (int): Maximum height for scaling videos. (default: 80)
  - cmap (str): Color map to use for depth movies. (default: "jet")
  - separate_by (Literal['default', 'groups', 'sessions', 'subjects']): Generate crowd movies by specified grouping. (default: default)
  - specific_syllable (Union[int, None]): Index of the specific syllable to render. (default: None)
  - session_names (List[str]): Specific sessions to create crowd movies from. (default: [])
  - scale (float): Scaling from pixel units to mm. (default: 1.0)
  - max_dur (Union[int, None]): Exclude syllables longer than this number of frames (None for no limit). (default: 60)
  - min_dur (int): Exclude syllables shorter than this number of frames. (default: 0)
  - legacy_jitter_fix (bool): Set to true if you notice jitter in your crowd movies. (default: False)
  - frame_path (str): Path to depth frames in h5 file. (default: "frames")
  - progress_bar (bool): Show verbose progress bars. (default: False)
  - pad (int): Pad crowd movie videos with this many frames. (default: 30)
  - seed (int): Defines random seed for selecting syllable instances to plot. (default: 0)
```

Finally, to generate the report, run the `make-report` command:
```sh
msq-maker make-report --config-file /path/to/msq-config.toml
```
