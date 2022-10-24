// Initialize the variables
const sequence_info = {"T1": "", "T2": ""};

// A function for setting the spinner visible or invisible
function setSpinnerVisible(visible) {
    let spinner = document.getElementById("spinner");
    if (visible) {
        // spinner.style = "";
        spinner.removeAttribute('style');
        spinner.style.visibility = "visible";
    } else {
        // spinner.style = "";
        spinner.removeAttribute('style');
        spinner.style.visibility = "hidden";
    }
}

// Check if the job is done
const intervalId = window.setInterval(function () {
    if (sessionStorage.getItem("job_id") !== null || sessionStorage.getItem("job_id") !== "") {

        fetch('/fileexist?' + new URLSearchParams({job_id: sessionStorage.getItem("job_id")}),
            {
                method: 'GET',
                headers: {
                    accept: 'application/json',
                },
            }).then(response => response.json()).then(data => {
            if (data.result === "true") {
                document.getElementById("btnDownload").style.enabled = true;
                window.clearInterval(intervalId);
                setSpinnerVisible(false);
                sessionStorage.setItem("spinner_state", "false");
                location.reload();
                location.reload();
            }
        })
    }
}, 10000);

// Initialize the frontend
document.addEventListener('DOMContentLoaded', function () {
    // Set the spinner invisible
    if (sessionStorage.getItem("spinner_state") !== null) {
        if (sessionStorage.getItem("spinner_state") === "true") {
            sessionStorage.setItem("spinner_state", "true");
            setSpinnerVisible(true);
        } else {
            sessionStorage.setItem("spinner_state", "false");
            setSpinnerVisible(false);
        }
    } else {
        setSpinnerVisible(false);
    }

    // Initialize the job id
    if (sessionStorage.getItem("job_id") === null) {
        sessionStorage.setItem("job_id", "");
    }

    // Initialize the dropdowns
    let dropdowns = document.querySelectorAll('select[id^=selector_sequence_]');
    [].forEach.call(dropdowns, function (div) {
        let sequence_info_ = JSON.parse(sessionStorage.sequence_info);

        if (sequence_info_["T1"] === "" || sequence_info_["T2"] === "") {
        } else {
            for (const key in sequence_info_) {
                if (sequence_info_[key].description === div.name) {
                    div.value = key;
                }
            }
        }
    });

}, false);


// Add event listener to upload button
document.getElementById('btnUpload').addEventListener('click', function (_) {
    // Show the spinner
    sessionStorage.setItem("spinner_state", "true");
    setSpinnerVisible(true);

    // Get the file
    let form_data = new FormData();
    let file = document.getElementById('file_upload').files[0];
    let ext = file.name.split('.').pop();
    form_data.append("file", file);

    // Check if the file is a zip file
    if (ext === "zip") {

        // Clear the local storage
        sessionStorage.sequence_info = JSON.stringify({"T1": "", "T2": ""});

        // Fetch the upload
        fetchUpload(form_data).then(function (data) {
            location.reload();
            sessionStorage.setItem("job_id", data.job_id);
            sessionStorage.setItem("spinner_state", "false");
            setSpinnerVisible(false);
        }).catch(function (error) {
            console.log(error);
            sessionStorage.setItem("spinner_state", "false");
            setSpinnerVisible(false);
        });
    } else {
        alert("Please upload only zip file!");
    }
});

// Fetch upload
async function fetchUpload(data) {
    const response = await fetch('/upload/', {
        method: 'POST',
        body: data,
    });
    const answer = await response.json();

    if (response.ok) {
        return answer;
    } else {
        throw new Error("Message" + answer.message + "Status" + answer.status);
    }
}

// Add event listener to assign button
document.getElementById('btnAssign').addEventListener('click', function (_) {
    // Show the spinner
    sessionStorage.setItem("spinner_state", "true");
    setSpinnerVisible(true);

    // Get the dropdowns
    let dropdowns = document.querySelectorAll('select[id^=selector_sequence_]');
    [].forEach.call(dropdowns, function (div) {
        sequence_info[div.value] = {
            uid: div.id.split('_')[2].toString(),
            description: div.name.toString(),
        };
    });

    // Add the sequence info to the local storage
    sessionStorage.sequence_info = JSON.stringify(sequence_info);

    // Check if the dropdown values are valid
    if (sequence_info["T1"].uid === "" || sequence_info["T2"].uid === "") {
        alert("Please select T1 and T2 images!");
    }
    if (sequence_info["T1"].uid === sequence_info["T2"].uid) {
        alert("T1 and T2 images cannot be same!");
    }

    // Fetch the assign
    let request_object = JSON.stringify({T1: sequence_info["T1"].uid, T2: sequence_info["T2"].uid})
    fetch('/assign/', {
        method: 'POST',
        body: request_object,
    }).then(response => response.json()
    ).then(data => {
        console.log("JobID: " + data.job_id);
        sessionStorage.job_id = data.job_id;
        sessionStorage.setItem("spinner_state", "true");
        setSpinnerVisible(true);
    }).catch(function (error) {
        console.log(error);
        sessionStorage.setItem("spinner_state", "false");
        setSpinnerVisible(false);
    });
});

// Add event listener to download button
document.getElementById('btnDownload').addEventListener('click', function (_) {
    // Fetch the download
    console.log("JobID: " + sessionStorage.getItem("job_id"));
    const url2 = new URL('/download', window.location.origin) + '?' + new URLSearchParams({job_id: sessionStorage.getItem("job_id")});
    console.log(url2);
    fetch(url2, {
        method: 'GET',
        headers: {
            accept: 'application/zip',
        }
    }).then(response => response.blob()
    ).then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.id = "download_link";
        a.style.display = 'none';
        a.href = url;
        a.download = sessionStorage.getItem("job_id") + '.zip';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    }).catch(error => {
        console.log(error);
    });
});

document.getElementById('btnClear').addEventListener('click', function (_) {
    sessionStorage.clear();
    sessionStorage.sequence_info = JSON.stringify({"T1": "", "T2": ""});

    fetch('/cancel_process', {
        method: 'POST',
        headers: {
            'Content-Type': 'text/plain',
        }
    }).then(response => response.text()).then(data => {
        return data;
    }).catch(error => {
        console.log(error);
    });
});