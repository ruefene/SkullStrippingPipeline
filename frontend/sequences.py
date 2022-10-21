import os
from typing import Dict
import json

import SimpleITK as sitk
from pyradise.utils import load_dataset_tag, Tag


def get_sequence_infos(path: str) -> Dict[str, str]:
    reader = sitk.ImageSeriesReader()
    series_uids = []

    for root, dirs, files in os.walk(path):
        series_uids.extend(reader.GetGDCMSeriesIDs(root))
    series_uids = list(set(series_uids))

    info = {}

    tags = (Tag(0x0008, 0x103e),  # Series Description
            Tag(0x0008, 0x0016))  # SOP Class UID
    for series_uid in series_uids:
        files = reader.GetGDCMSeriesFileNames(path, series_uid, recursive=True)

        dataset = load_dataset_tag(files[0], tags)
        sop_class_uid = str(dataset.get('SOPClassUID'))

        if sop_class_uid != '1.2.840.10008.5.1.4.1.1.4':
            continue

        series_desc = str(dataset.get('SeriesDescription'))
        info[series_uid] = series_desc

    return info


def generate_modality_config(path: str,
                             info: Dict[str, str]
                             ) -> bool:
    if os.path.basename(path) == '0' or path is None:
        return False

    # use SimpleITK for extracting the series uids
    reader = sitk.ImageSeriesReader()
    available_series_uids = []

    for root, dirs, files in os.walk(path):
        available_series_uids.extend(reader.GetGDCMSeriesIDs(root))
    available_series_uids = list(set(available_series_uids))

    # get the files associated with the series uids
    config = []
    for series_uid, modality in info.items():

        # check if the series uid is available
        if series_uid not in available_series_uids:
            raise ValueError(f'Series UID {series_uid} not available in {path}')

        files = reader.GetGDCMSeriesFileNames(path, series_uid, recursive=True)

        # load the necessary tags
        tags = (Tag(0x0008, 0x0060),  # Modality
                Tag(0x0008, 0x0016),  # SOP Class UID
                Tag(0x0020, 0x000e),  # Series Instance UID
                Tag(0x0020, 0x000d),  # Study Instance UID
                Tag(0x0020, 0x0011),  # Series Number
                Tag(0x0008, 0x103e))  # Series Description
        dataset = load_dataset_tag(files[0], tags)

        # append to the config
        entry = {'SOPClassUID': str(dataset.get('SOPClassUID')),
                 'StudyInstanceUID': str(dataset.get('StudyInstanceUID')),
                 'SeriesInstanceUID': str(dataset.get('SeriesInstanceUID')),
                 'SeriesDescription': str(dataset.get('SeriesDescription')),
                 'SeriesNumber': str(dataset.get('SeriesNumber')),
                 'DICOM_Modality': str(dataset.get('Modality')),
                 'Modality': modality}
        config.append(entry)

    # write the config
    config_path = os.path.join(path, 'modality_config.json')
    with open(config_path, 'w+') as f:
        json.dump(config, f, indent=4)

    return True
