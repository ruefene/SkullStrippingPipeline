# SkullStrippingPipeline
This repository contains a Docker-based auto-segmentation pipeline example relying on the [PyRaDiSe Python package](https://github.com/ubern-mia/pyradise).

## Installation
Clone the repository by typing the following command in your terminal:
```
git clone https://github.com/ruefene/SkullStrippingPipeline.git
```

Navigate to the ```data/model``` directory and download the example model file from the [PyRaDiSe example data repository](https://github.com/ruefene/pyradise-example-data):
```
cd SkullStrippingPipeline/data/model
curl -LJO https://github.com/ruefene/pyradise-example-data/raw/main/model/model.pth
```

Then, go to the repository folder and build the Docker image by typing the following command:
```
cd SkullStrippingPipeline
docker build -t ch.unibe.segmentation.skullstripping .
```

## Usage
To run the pipeline, type the following command in your terminal:
```
docker run -p 4000:5000 --name SkullStripper --gpus all ch.unibe.segmentation.skullstripping 
```

After starting the container, you can access the web interface by typing the following URL in your browser:
```
http://localhost:4000
```

## Run without Docker
For running this example without using Docker you need to set several environment variables. 
The following table shows the required environment variables and their default values:

| Variable               | Example value                                | Description                                                         |
|------------------------|----------------------------------------------|---------------------------------------------------------------------|
| ```MODEL_DIR_PATH```   | ```C:\SkullStrippingPipeline\data\model```   | The directory where the model is stored.                            |
| ```INPUT_DATA_DIR```   | ```C:\SkullStrippingPipeline\data\input```   | The directory where the input data is uploaded to.                  |
| ```OUTPUT_DATA_DIR```  | ```C:\SkullStrippingPipeline\data\output```  | The directory where the output data will be stored before download. |
| ```SCRATCH_DATA_DIR``` | ```C:\SkullStrippingPipeline\data\scratch``` | The directory where the temporary data gets stored.                 |



## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
