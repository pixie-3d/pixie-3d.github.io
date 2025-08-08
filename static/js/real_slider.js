/* Real-world interactive slider – adapted from GARField project page */

/* ---- CONSTANTS YOU CARE ABOUT ---- */
const SEGMENT_COUNT = 5;
const PANE_WIDTH = 960;          // must match Python
const PANE_HEIGHT = 540;
const VIDEO_ASPECT_RATIO =          // width ÷ height of the *whole* concat video
    PANE_WIDTH / PANE_HEIGHT;   // 3200 / 360 ≈ 8.888



/* Scenes available for real-world demo */
const videoNames = [
    "bouquet",
    "bonsai",
    "vasedeck",
];

/* Map from scene → video path (concatenated RGB|material|E|density|nu) */
const videoPathMap = {
    vasedeck: "static/videos/ours_real_world/renders/vasedeck/concat.mp4",
    bonsai: "static/videos/ours_real_world/renders/bonsai/concat.mp4",
    bouquet: "static/videos/ours_real_world/renders/bouquet/concat.mp4"
};

let videos = [];
let currentVideoIdx = 0;
// Width of the displayed canvas (updated on resize)
// Which feature to show on the right pane: 0-material, 1-E, 2-density, 3-nu
let displayLevel = 0;

function buildHiddenVideos() {
    const realSection = document.getElementById("real");
    if (!realSection) return;
    const frag = document.createDocumentFragment();
    videoNames.forEach((name) => {
        const vid = document.createElement("video");
        vid.id = name;
        vid.className = "videos";
        vid.muted = true;
        vid.loop = true;
        vid.autoplay = true;
        vid.setAttribute("playsinline", "");
        vid.style.display = "none";

        const source = document.createElement("source");
        source.src = videoPathMap[name];
        source.type = "video/mp4";
        vid.appendChild(source);
        frag.appendChild(vid);
    });
    realSection.appendChild(frag);
}

function loadVideos() {
    videos = videoNames.map((n) => document.getElementById(n));
}

function resizeCanvas() {
    const mainResults = document.getElementById("image-compare-canvas");
    if (!mainResults) return;
    const w = mainResults.offsetWidth;
    const h = w / VIDEO_ASPECT_RATIO;
    mainResults.height = h;
    mainResults.style.height = h + "px";
    videoWidth = w;

    const canvas = document.getElementById("canvas");
    if (canvas) {
        canvas.width = w;
        canvas.height = h;
        canvas.style.width = w + "px";
        canvas.style.height = h + "px";
    }
}

window.addEventListener("load", () => {
    buildHiddenVideos();
    resizeCanvas();
    loadVideos();
    if (videos[0]) {
        videos[0].play();
    }
});

window.addEventListener("resize", resizeCanvas);

/* jQuery powered interactions */
$(function () {
    /* IMAGE-COMPARE UI */
    $(".image-compare").each((_i, parent) => {
        const $p = $(parent);
        const before = $p.data("before-label") || "Before";
        const after = $p.data("after-label") || "After";
        $p.append(
            "<div class='image-compare-handle'><i class='ti ti-arrows-horizontal'></i></div>" +
            "<div class='image-compare-before'><div>" +
            before +
            "</div></div>" +
            "<div class='image-compare-after'><div>" +
            after +
            "</div></div>"
        );
    });

    /* Draw loop */
    setInterval(() => {
        if (videos.length === 0) return;
        const $parent = $("#image-compare-canvas");
        const $handle = $parent.find(".image-compare-handle");
        const currentLeft = $handle.position().left;
        const Kp = 0.06;
        const Kd = 0.25;
        let velocity = $parent.data("velocity") || 0;
        let targetLeft = $parent.data("targetX");
        if (targetLeft !== undefined) {
            const padding = 10;
            const parentWidth = $parent.width();
            if (targetLeft <= padding) targetLeft = 0;
            if (targetLeft >= parentWidth - padding) targetLeft = parentWidth;
            const delta = targetLeft - currentLeft;
            velocity += Kp * delta;
        }
        velocity -= Kd * velocity;
        $parent.data("velocity", velocity);
        const newLeft = currentLeft + velocity;

        $handle.css("left", newLeft + "px");
        $parent.find(".image-compare-before").width(newLeft + "px");
        $parent
            .find(".image-compare-after")
            .css({ left: newLeft + "px", width: videoWidth - newLeft + "px" });

        const canvas = document.getElementById("canvas");
        const ctx = canvas.getContext("2d");
        const video = videos[currentVideoIdx];
        if (!video) return;

        /* Calculate per-segment dimensions based on the actual video resolution. */
        const segmentWidth = (video.videoWidth || 960) / SEGMENT_COUNT;
        const segmentHeight = video.videoHeight || 520;

        /* Map handle position (newLeft) from canvas space → video segment space. */
        const scaledLeft = (newLeft * segmentWidth) / videoWidth;

        /* Draw RGB (left pane) */
        ctx.drawImage(
            video,
            0,
            0,
            scaledLeft,
            segmentHeight,
            0,
            0,
            newLeft,
            videoWidth / VIDEO_ASPECT_RATIO
        );

        /* Draw selected feature (right pane) */
        ctx.drawImage(
            video,
            segmentWidth * (displayLevel + 1) + scaledLeft,
            0,
            segmentWidth - scaledLeft,
            segmentHeight,
            newLeft,
            0,
            videoWidth - newLeft,
            videoWidth / VIDEO_ASPECT_RATIO
        );
    }, 10);

    /* adjust PD gains for snappier feel */
    const Kp_fast = 0.06;
    const Kd_fast = 0.25;

    /* Drag logic */
    $(".image-compare").on("mousedown touchstart", (evt) => {
        const $parent = $(evt.currentTarget);
        $parent.data("dragging", true);
        const x = evt.type === "mousedown" ? evt.pageX : evt.touches[0].pageX;
        $parent.data("targetX", x - $parent.offset().left);
    });
    $(document)
        .on("mouseup touchend", () => {
            $(".image-compare").data("dragging", false);
        })
        .on("mousemove touchmove", (evt) => {
            $(".image-compare").each((_i, parent) => {
                const $p = $(parent);
                if (!$p.data("dragging")) return;
                const x = evt.type === "mousemove" ? evt.pageX : evt.touches[0].pageX;
                $p.data("targetX", x - $p.offset().left);
            });
        });

    /* Hierarchy switcher */
    $(".switcher").each((switcherIdx, switcherEl) => {
        const $s = $(switcherEl);
        const $container = $("<div>", { class: "switcher-labels" });
        let $current = null;
        $s.children().each((childIdx, child) => {
            const $child = $(child);
            const id = `switcher-${switcherIdx}-${childIdx}`;
            const $input = $("<input>", {
                type: "radio",
                name: `switcher-${switcherIdx}`,
                id,
                checked: childIdx === 0
            }).on("click", () => {
                $current.addClass("switcher-hidden");
                displayLevel = childIdx;
                $current = $().add($child).add($input).add($label);
                $current.removeClass("switcher-hidden");
            });
            const $label = $("<label>", { text: $child.data("switcher-label"), for: id });
            $container.append($("<div>").append($input, $label));
            if (childIdx !== 0) {
                $child.addClass("switcher-hidden");
                $input.addClass("switcher-hidden");
                $label.addClass("switcher-hidden");
            } else {
                $current = $().add($child).add($input).add($label);
            }
        });
        const $title = $("<label>", { text: `${$s.data("switcher-title")}:` });
        $container.prepend($title);
        $s.append($container);
    });

    /* Thumbnail carousel */
    $(".results-slide-row").each((_idx, row) => {
        const $row = $(row);
        $row.children().each((childIdx, child) => {
            const $child = $(child);
            const btn = $("<button>", { class: "thumbnail-btn" }).on("click", () => {
                // mark active thumbnail
                $(".thumbnail-btn").removeClass("active");
                btn.addClass("active");
                currentVideoIdx = childIdx;
                const vid = videos[currentVideoIdx];
                vid.currentTime = 0;
                vid.play();
                update_play_icon();
            });
            const img = $("<img>", { class: "thumbnails", src: $child.data("img-src"), alt: $child.data("label") });
            const label = $("<span>", { class: "thumbnail_label", text: $child.data("label") });
            btn.append(img, label);
            $row.append(btn);

            // set the first thumbnail as active by default
            if (childIdx === 0) {
                btn.addClass("active");
            }
        });
    });
});

/* Carousel arrow helpers */
function results_slide_left() {
    document.getElementById("results-objs-scroll").scrollLeft = 0;
}
function results_slide_right() {
    document.getElementById("results-objs-scroll").scrollLeft += 1000;
}

/* Basic video controls */
function update_play_icon() {
    const btn = document.getElementById("play-btn");
    const vid = videos[currentVideoIdx];
    if (!btn || !vid) return;
    if (vid.paused) {
        btn.classList.remove("fa-pause");
        btn.classList.add("fa-play");
    } else {
        btn.classList.add("fa-pause");
        btn.classList.remove("fa-play");
    }
}

function play_pause() {
    const vid = videos[currentVideoIdx];
    if (!vid) return;
    if (vid.paused) vid.play();
    else vid.pause();
    update_play_icon();
}

function fullscreen() {
    const vid = videos[currentVideoIdx];
    if (!vid) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else vid.requestFullscreen();
} 