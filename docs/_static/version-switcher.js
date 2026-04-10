(function () {
    "use strict";

    function isVersionSegment(value) {
        return /^\d+\.\d+\.\d+$/.test(value) || value === "latest";
    }

    function pathInfo() {
        var parts = window.location.pathname.split("/").filter(Boolean);
        var versionIndex = -1;
        for (var index = 0; index < parts.length; index += 1) {
            if (isVersionSegment(parts[index])) {
                versionIndex = index;
                break;
            }
        }
        if (versionIndex === -1) {
            return null;
        }
        return {
            baseParts: parts.slice(0, versionIndex),
            version: parts[versionIndex],
            suffixParts: parts.slice(versionIndex + 1)
        };
    }

    function toPath(parts) {
        return "/" + parts.join("/");
    }

    function addSwitcher(versions, info) {
        var nav = document.querySelector(".wy-side-nav-search");
        if (!nav || !versions.length) {
            return;
        }
        var switcherVersions = versions.slice();
        if (switcherVersions.indexOf(info.version) === -1) {
            switcherVersions.unshift(info.version);
        }

        var container = document.createElement("div");
        container.className = "dg-version-switcher";

        var label = document.createElement("label");
        label.setAttribute("for", "dg-version-switcher-select");
        label.textContent = "Version";
        container.appendChild(label);

        var select = document.createElement("select");
        select.id = "dg-version-switcher-select";

        switcherVersions.forEach(function (version) {
            var option = document.createElement("option");
            option.value = version;
            option.textContent = version;
            option.selected = (version === info.version);
            select.appendChild(option);
        });

        select.addEventListener("change", function (event) {
            var nextVersion = event.target.value;
            var nextParts = info.baseParts.concat([nextVersion], info.suffixParts);
            window.location.assign(toPath(nextParts));
        });

        container.appendChild(select);
        nav.appendChild(container);
    }

    function getVersionsUrl(info) {
        return toPath(info.baseParts.concat(["versions.json"]));
    }

    function start() {
        var info = pathInfo();
        if (!info) {
            return;
        }
        fetch(getVersionsUrl(info))
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Unable to load versions.json");
                }
                return response.json();
            })
            .then(function (versions) {
                if (Array.isArray(versions)) {
                    addSwitcher(versions, info);
                }
            })
            .catch(function () {
                // Keep docs usable even if versions.json is unavailable.
            });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
}());
