import argparse
import joblib


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('model', help='Model file path.')
    parser.add_argument('dest', help='Destination path for the modified model.')
    parser.add_argument('--cast-dtypes', action='store_true', help='Cast labels to int16 dtype.')
    parser.add_argument('--remove-model', action='store_true', help='Remove the model key.')

    args = parser.parse_args()

    # load the model
    model_obj = joblib.load(args.model)

    # correct dtype of labels
    if args.cast_dtypes:
        
        for i, labels in enumerate(model_obj['labels']):
            model_obj['labels'][i] = labels.astype('int16')

    # remove model key
    if args.remove_model:
        model_obj.pop('model')

    # save the modified model
    joblib.dump(model_obj, args.dest, compress=0)


if __name__ == '__main__':
    main()
