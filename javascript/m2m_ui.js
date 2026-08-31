/**
 * Marshal the arguments for a mov2mov generation request.
 *
 * Gradio calls this with the tab's input values followed by the current values
 * of the event's outputs. Forge's own create_submit_args() strips that suffix by
 * guessing where it starts (it looks for the gallery array txt2img/img2img put
 * first among their outputs). mov2mov's outputs start with a video, so that
 * guess is wrong here and silently truncates real arguments as soon as a
 * script's last control holds a list. Python passes the exact input count
 * instead, which cannot drift.
 */
function submit_mov2mov(args, inputCount) {
    const res = Array.from(args).slice(0, inputCount);
    while (res.length < inputCount) res.push(null);

    const id = randomId();
    res[0] = id;
    res[1] = 2;

    // Never let a DOM lookup stop the request from being sent: a throw here
    // rejects the frontend function and Generate would appear to do nothing.
    try {
        localSet("mov2mov_task_id", id);
        showSubmitButtons("mov2mov", false);
        showResultVideo("mov2mov", false);

        requestProgress(
            id,
            gradioApp().getElementById("mov2mov_gallery_container"),
            gradioApp().getElementById("mov2mov_gallery"),
            function () {
                showSubmitButtons("mov2mov", true);
                showResultVideo("mov2mov", true);
                localRemove("mov2mov_task_id");
            },
        );
    } catch (error) {
        console.error("mov2mov: could not attach the progress bar", error);
    }

    return res;
}

/** Swap between the live-preview gallery and the finished video player. */
function showResultVideo(tabname, show) {
    const video = gradioApp().getElementById(tabname + "_video");
    const gallery = gradioApp().getElementById(tabname + "_gallery");

    if (video) video.style.display = show ? "block" : "none";
    if (gallery) gallery.style.display = show ? "none" : "block";
}

function copy_from(type) {
    return [];
}

/**
 * Resolution of the loaded source video, for the "Resize by" preview and the
 * auto-detect button. Returns zeroes until a video is loaded and its metadata
 * has been read.
 */
function currentMov2movSourceResolution(w, h, scaleBy) {
    const video = gradioApp().querySelector("#mov2mov_mov video");

    if (video && video.videoWidth && video.videoHeight) {
        return [video.videoWidth, video.videoHeight, scaleBy];
    }
    return [0, 0, scaleBy];
}
