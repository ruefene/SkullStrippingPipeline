import os
from typing import (Any, Dict, Optional)

import numpy as np
import torch
import torch.nn as nn
import pyradise.process as ps_proc
import pyradise.data as ps_data

from .network import UNet


class ExampleInferenceFilter(ps_proc.InferenceFilter):
    """An example implementation of an InferenceFilter for
    slice-wise segmentation with a PyTorch-based U-Net."""

    def __init__(self) -> None:
        super().__init__()

        # Define the device on which the model should be run
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Define a class attribute for the model
        self.model: Optional[nn.Module] = None

    def _prepare_model(self,
                       model: nn.Module,
                       model_path: str
                       ) -> nn.Module:
        """Implementation using the PyTorch framework."""

        # Load model parameters
        model.load_state_dict(torch.load(model_path, map_location=self.device))

        # Assign the model to the class
        self.model = model.to(self.device)

        # Set model to evaluation mode
        self.model.eval()

        return model

    def _infer_on_batch(self,
                        batch: Dict[str, Any],
                        params: ps_proc.InferenceFilterParams
                        ) -> Dict[str, Any]:
        """Implementation using the PyTorch framework."""

        # Stack and adjust the numpy array such that it fits the
        # [batch, channel / images, height, width, (depth)] format
        # Note: The following statement works for slice-wise and patch-wise processing
        if (loop_axis := params.indexing_strategy.loop_axis) is None:
            adjusted_input = np.stack(batch['data'], axis=0)
        else:
            adjusted_input = np.stack(batch['data'], axis=0).squeeze(loop_axis + 2)

        # Generate a tensor from the numpy array
        input_tensor = torch.from_numpy(adjusted_input)

        # Move the batch to the same device as the model
        input_tensor = input_tensor.to(self.device, dtype=torch.float32)

        # Apply the model to the batch
        with torch.no_grad():
            output_tensor = self.model(input_tensor)

        # Retrieve the predicted classes from the output
        final_activation_fn = nn.Sigmoid()
        output_tensor = (final_activation_fn(output_tensor) > 0.5).bool()

        # Convert the output to a numpy array
        # Note: The output shape must be [batch, height, width, (depth)]
        output_array = output_tensor.cpu().numpy()

        # Construct a list of output arrays such that it fits the index expressions
        batch_output_list = [output_array[i, ...] for i in range(output_array.shape[0])]

        # Combine the output arrays into a dictionary
        output = {'data': batch_output_list,
                  'index_expr': batch['index_expr']}

        return output


def get_pipeline(model_path: str) -> ps_proc.FilterPipeline:
    # Construct a pipeline the processing
    pipeline = ps_proc.FilterPipeline()

    # Construct and ddd the preprocessing filters to the pipeline
    output_size = (256, 256, 256)
    output_spacing = (1.0, 1.0, 1.0)
    reference_modality = 'T1'
    resample_filter_params = ps_proc.ResampleFilterParams(output_size,
                                                          output_spacing,
                                                          reference_modality=reference_modality,
                                                          centering_method='reference')
    resample_filter = ps_proc.ResampleFilter()
    pipeline.add_filter(resample_filter, resample_filter_params)

    norm_filter_params = ps_proc.ZScoreNormFilterParams()
    norm_filter = ps_proc.ZScoreNormFilter()
    pipeline.add_filter(norm_filter, norm_filter_params)

    # Construct and add the inference filter
    modalities_to_use = ('T1', 'T2')
    inf_params = ps_proc.InferenceFilterParams(model=UNet(num_channels=2, num_classes=1),
                                               model_path=model_path,
                                               modalities=modalities_to_use,
                                               reference_modality=reference_modality,
                                               output_organs=(ps_data.Organ('Skull'),),
                                               output_annotator=ps_data.Annotator('AutoSegmentation'),
                                               organ_indices=(1,),
                                               batch_size=os.environ.get('BATCH_SIZE', 4),
                                               indexing_strategy=ps_proc.SliceIndexingStrategy(0))

    inf_filter = ExampleInferenceFilter()
    pipeline.add_filter(inf_filter, inf_params)

    # Add postprocessing filters
    cc_filter_params = ps_proc.SingleConnectedComponentFilterParams()
    cc_filter = ps_proc.SingleConnectedComponentFilter()
    pipeline.add_filter(cc_filter, cc_filter_params)

    return pipeline
