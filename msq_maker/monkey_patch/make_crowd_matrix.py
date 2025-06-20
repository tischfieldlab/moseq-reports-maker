

import cv2
import h5py
import moseq2_viz.viz
import numpy as np

def is_detectron_extraction(h5: h5py.File) -> bool:
    """Check if the extraction metadata indicates a Detectron2 extraction.

    Args:
        h5 (h5py.File): HDF5 file object containing the metadata.

    Returns:
        bool: True if the extraction is from Detectron2, False otherwise.
    """
    if 'metadata/extraction/extract_version' in h5:
        return str(h5['metadata/extraction/extract_version'][()]).startswith('moseq2-detectron-extract')
    else:
        return False



def make_crowd_matrix_d2_compat(slices, nexamples=50, pad=30, raw_size=(512, 424), outmovie_size=(300, 300), frame_path='frames',
                      crop_size=(80, 80), max_dur=60, min_dur=0, scale=1,
                      center=False, rotate=False, select_median_duration_instances=False, min_height=10, legacy_jitter_fix=False,
                      seed=0, **kwargs):
    """
    Creates crowd movie video numpy array.

    Args:
    slices (np.ndarray): video slices of specific syllable label
    nexamples (int): maximum number of mice to include in crowd_matrix video
    pad (int): number of frame padding in video
    raw_size (tuple): video dimensions.
    frame_path (str): variable to access frames in h5 file
    crop_size (tuple): mouse crop size
    max_dur (int or None): maximum syllable duration.
    min_dur (int): minimum syllable duration.
    scale (int): mouse size scaling factor.
    center (bool): boolean flag that indicates whether mice are centered.
    rotate (bool): boolean flag that indicates wehther to rotate mice and orient them.
    select_median_duration_instances (bool): flag that indicates wehther to select examples with syallable duration closer to median.
    min_height (int): minimum max height from floor to use.
    legacy_jitter_fix (bool): flag that indicates wehther to apply jitter fix for K1 camera.
    kwargs (dict): extra keyword arguments

    Returns:
    crowd_matrix (np.ndarray): crowd movie for a specific syllable.
    """

    if rotate and not center:
        raise NotImplementedError('Rotating without centering not supported')

    rng = np.random.default_rng(seed)

    # set up x, y value to crop out the mouse with respect to the mouse centriod
    xc0, yc0 = crop_size[1] // 2, crop_size[0] // 2
    xc = np.arange(-xc0, xc0 + 1, dtype='int16')
    yc = np.arange(-yc0, yc0 + 1, dtype='int16')

    # compute syllable duration in the sample
    durs = np.array([i[1]-i[0] for i, _, _ in slices])

    if max_dur is not None:
        idx = np.where(np.logical_and(durs < max_dur, durs > min_dur))[0]
        use_slices = [_slice for i, _slice in enumerate(slices) if i in idx]
        # return the sort order of durations of the remaining slices
        dur_order = np.argsort(durs[idx])
    else:
        max_dur = durs.max()
        idx = np.where(durs > min_dur)[0]
        use_slices = [_slice for i, _slice in enumerate(slices) if i in idx]
        # return the sort order of durations of the remaining slices
        dur_order = np.argsort(durs[idx])

    if len(use_slices) > nexamples:
        if select_median_duration_instances:
            # choose the nexamples near median duration
            selction_begin = int(len(dur_order)//2 - nexamples//2)
            # ensure nexamples are picked
            selection_end = selction_begin + nexamples
            use_slices = [_slice for i, _slice in enumerate(use_slices) if i in dur_order[selction_begin:selection_end]]
        else:
            use_slices = rng.permutation(use_slices)[:nexamples]

    if len(use_slices) == 0 or max_dur < 0:
        return None

    crowd_matrix = np.zeros((max_dur + pad * 2, raw_size[1], raw_size[0]), dtype='uint8')

    for idx, _, fname in use_slices:
        # pad frames before syllable onset, and add max_dur and padding after syllable onset
        use_idx = (idx[0] - pad, idx[0] + max_dur + pad)
        idx_slice = slice(*use_idx)

        # get the frames, combine in a way that's alpha-aware
        with h5py.File(fname, 'r') as h5:
            is_d2_extract = is_detectron_extraction(h5)
            nframes = len(h5[frame_path])

            if 'centroid_x' in h5['scalars']:
                use_names = ('scalars/centroid_x', 'scalars/centroid_y')
            elif 'centroid_x_px' in h5['scalars']:
                use_names = ('scalars/centroid_x_px', 'scalars/centroid_y_px')

            if use_idx[0] < 0 or use_idx[1] >= nframes - 1:
                continue

            # select centroids
            centroid_x = h5[use_names[0]][idx_slice]
            centroid_y = h5[use_names[1]][idx_slice]

            # center the mice such that when it is syllable onset, the mice's centroids are in the center
            if center:
                centroid_x -= centroid_x[pad]
                centroid_x += raw_size[0] // 2
                centroid_y -= centroid_y[pad]
                centroid_y += raw_size[1] // 2

            angles = h5['scalars/angle'][idx_slice]
            frames = moseq2_viz.viz.clean_frames((h5[frame_path][idx_slice] / scale).astype('uint8'), **kwargs)

            # flip the mouse in the correct orientation if necessary
            if 'flips' in h5['metadata/extraction']:
                # h5 format as of v0.1.3
                flips = h5['metadata/extraction/flips'][idx_slice]
                if not is_d2_extract:
                    # if not a detectron2 extraction, flip angles
                    angles[np.where(flips == True)] -= np.pi
            elif 'flips' in h5['metadata']:
                # h5 format prior to v0.1.3
                flips = h5['metadata/flips'][idx_slice]
                if not is_d2_extract:
                    # if not a detectron2 extraction, flip angles
                    angles[np.where(flips == True)] -= np.pi
            else:
                flips = np.zeros(angles.shape, dtype='bool')

        angles = np.rad2deg(angles)

        for i in range(len(centroid_x)):

            if np.any(np.isnan([centroid_x[i], centroid_y[i]])):
                continue

            # set up the rows and columnes to crop the video
            rr = (yc + int(centroid_y[i])).astype('int16')
            cc = (xc + int(centroid_x[i])).astype('int16')
            if np.any(rr >= raw_size[1]) or np.any(cc >= raw_size[0]): continue

            if ((rr[-1] - rr[0]) != crop_size[0]) or ((cc[-1] - cc[0]) != crop_size[1]):
                continue

            if np.any(rr < 0) or np.any(cc < 0):
                top = 0
                if np.any(rr < 0):
                    top = rr.min()
                    rr = rr - rr.min()
                left = 0
                if np.any(cc < 0):
                    left = cc.min()
                    cc = cc - cc.min()
                new_frame_clip = cv2.copyMakeBorder(frames[i].copy(), abs(top), 0, abs(left), 0, cv2.BORDER_CONSTANT, value=0)
                if left > 0:
                    new_frame_clip = new_frame_clip[:, :crop_size[1]]
                if top > 0:
                    new_frame_clip = new_frame_clip[:crop_size[0]]
            else:
                new_frame_clip = frames[i].copy()

            if is_d2_extract:
                # for detectron2 extraction, angles are should be negated
                rot_mat = cv2.getRotationMatrix2D((xc0, yc0), -angles[i], 1)
            else:
                rot_mat = cv2.getRotationMatrix2D((xc0, yc0), angles[i], 1)

            # add the new instance to the exisiting crowd matrix
            old_frame = crowd_matrix[i]
            new_frame = np.zeros_like(old_frame)

            if not is_d2_extract:
                # change from fliplr, removes jitter since we now use rot90 in moseq2-extract
                if flips[i] and legacy_jitter_fix:
                    new_frame_clip = np.fliplr(new_frame_clip)
                elif flips[i]:
                    new_frame_clip = np.rot90(new_frame_clip, k=-2)

            new_frame_clip = cv2.warpAffine(new_frame_clip.astype('float32'),
                                            rot_mat, crop_size).astype(frames.dtype)

            if i >= pad and i <= pad + (idx[1] - idx[0]):
                cv2.circle(new_frame_clip, (xc0, yc0), 3, (255, 255, 255), -1)

            new_frame[rr[0]:rr[-1], cc[0]:cc[-1]] = new_frame_clip

            if rotate:
                rot_mat = cv2.getRotationMatrix2D((raw_size[0] // 2, raw_size[1] // 2),
                                                -angles[pad] + flips[pad] * 180,
                                                1)
                new_frame = cv2.warpAffine(new_frame, rot_mat, raw_size).astype(new_frame.dtype)

            # zero out based on min_height before taking the non-zeros
            new_frame[new_frame < min_height] = 0
            old_frame[old_frame < min_height] = 0

            new_frame_nz = new_frame > 0
            old_frame_nz = old_frame > 0

            blend_coords = np.logical_and(new_frame_nz, old_frame_nz)
            overwrite_coords = np.logical_and(new_frame_nz, ~old_frame_nz)

            old_frame[blend_coords] = .5 * old_frame[blend_coords] + .5 * new_frame[blend_coords]
            old_frame[overwrite_coords] = new_frame[overwrite_coords]

            crowd_matrix[i] = old_frame

    # compute non-zero pixels across all frames
    non_zero_coor = np.argwhere(np.any(crowd_matrix>0, 0))

    try:
        # find min max coordinates to crop out the blanks
        min_xy = np.min(non_zero_coor, 0)
        max_xy = np.max(non_zero_coor, 0)
        # crop out the blanks while making sure the slice is not zero
        if np.all(max_xy - min_xy) > 0:
            crowd_matrix = crowd_matrix[:, min_xy[0]:max_xy[0], min_xy[1]:max_xy[1]]

            # pad crowd movies to outmovie_size if the dimension is smaller than outmoive_size
            if np.all(outmovie_size > max_xy - min_xy):
                x_pad, y_pad = (outmovie_size - (max_xy - min_xy))//2
                crowd_matrix = np.pad(crowd_matrix, ((0,0), (x_pad, x_pad), (y_pad, y_pad)), 'constant', constant_values=0)

    except ValueError:
        print('No mouse in the crowd movie')

    return crowd_matrix


# Monkey patch the make_crowd_matrix function in moseq2_viz.viz to enable compatibility with Detectron2 extractions
moseq2_viz.viz.make_crowd_matrix = make_crowd_matrix_d2_compat
