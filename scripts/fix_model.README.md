# About `fix_model.py`

Although the `moseq-reports-maker` package has no hard dependency on the [`moseq2-model`](https://github.com/dattalab/moseq2-model) package, if your model was generated using the `--save-model True` parameter (by default `True`), loading the model will require installation of the `moseq2-model` package, as unpickling the `model` key within the saved model `dict` would require `moseq2-model` classes and their dependencies.

An alternative workaround is to use this script to remove the `model` key from the model `dict` and save the result back to disk. This can make the model more portable (accessible on OS's that are not supported by `moseq2-model`, ex Windows), and allow you to load the model without having `moseq2-model` installed in your environment. For this option, see the script `fix_model.py` and the associated `fix_model.README.md` in the scripts folder of this repo.

## Using this script
You should run this script under an active environment that has `moseq2-model` installed. It takes as positional arguments the input model pickle file and the destination filename. Options control the manipulations performed on the model.
```sh
python fix_model.py [options] <source-model> <destination-model>
```

Here is an example command with parameters (adjust as needed):
```sh
python fix_model.py --remove-model my_model.p my_model.fixed.p
```

This will produce a new model file named `my_model.fixed.p` that omits the `model` key.

Older versions of the moseq framework saved model labels with a `uint16` dtype, while newer models save labels with a `uint32` dtype. For compatibility with older scripts, the `fix_model.py` script can also recast labels with the `uint16` dtype if you pass the `--cast-dtypes` option.