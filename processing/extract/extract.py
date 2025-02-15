import os
from shutil import copyfile

from fame.core.module import (
    ProcessingModule,
    ModuleInitializationError,
    ModuleExecutionError,
)
from fame.common.utils import tempdir

from ..docker_utils import HAVE_DOCKER, docker_client, docker


class Extract(ProcessingModule):
    name = "extract"
    description = "Extract most compressed archives (zip, rar, 7z...)"
    acts_on = ["zip", "rar", "7z", "iso"]

    config = [
        {
            "name": "password_candidates",
            "type": "text",
            "default": "virus\ninfected",
            "description": "List of passwords to try when unpacking an encrypted archive file (one per line).",
        },
        {
            "name": "maximum_extracted_files",
            "type": "integer",
            "default": 5,
            "description": "If there are more files than this value in the archive, files will not be extracted.",
        },
        {
            "name": "maximum_automatic_analyses",
            "type": "integer",
            "default": 1,
            "description": "If there are more files than this value in the archive, no analyses will be automatically created for extracted files.",
        },
    ]

    def initialize(self):
        if not HAVE_DOCKER:
            raise ModuleInitializationError(self, "Missing dependency: docker")
        return True

    def save_output(self, output):
        namelist = []
        for line in output.splitlines():
            if line.startswith("warning:"):
                self.results["warnings"].append(line.lstrip("warning: "))
            elif line.startswith("should_analyze:"):
                base_path = line.replace("should_analyze: /data/output/", "")
                filepath = os.path.join(self.results_dir, base_path)
                namelist.append(base_path)
                if os.path.isfile(filepath):
                    self.add_extracted_file(filepath)
            else:
                self.log("debug", line)

        self.results["files"] = namelist

    def extract(self, file):
        args = '"{}" {} {}'.format(
            file, self.maximum_extracted_files, self.maximum_automatic_analyses
        )

        try:
            # start the right docker
            output = docker_client.containers.run(
                "fame/extract",
                args,
                volumes={self.outdir: {"bind": "/data", "mode": "rw"}},
                stderr=True,
                stdout=True,
                remove=True,
            )
        except (docker.errors.ContainerError, docker.errors.APIError) as e:
            if hasattr(e, "stderr"):
                e = e.stderr
            elif hasattr(e, "explanation"):
                e = e.explanation
            if type(e) is bytes:
                e = e.decode("utf-8", errors="replace")
            raise ModuleExecutionError(e)

        if type(output) is bytes:
            output = output.decode("utf-8", errors="replace")

        return output

    def each(self, target):
        self.results = {"warnings": []}

        # Create temporary directory to get results
        self.outdir = tempdir()

        self.results_dir = os.path.join(self.outdir, "output")

        if not os.path.isdir(self.results_dir):
            os.mkdir(self.results_dir)

        with open(os.path.join(self.outdir, "passwords_candidates.txt"), "w+") as f:
            f.write(self.password_candidates)

        copyfile(target, os.path.join(self.outdir, os.path.basename(target)))
        target = os.path.join("/data/", os.path.basename(target))
        # execute docker container
        output = self.extract(target)

        # save log output from dockerized app, extract potential redirections
        self.save_output(output)

        return True


class Zip(Extract):
    name = "zip"
    description = "Extract zip archive content"
    acts_on = ["zip"]
