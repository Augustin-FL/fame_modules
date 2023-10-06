import glob
import pathlib
import hashlib
import pyzbar

from fame.core.module import ProcessingModule, ModuleInitializationError, ModuleExecutionError
from fame.common.utils import tempdir

try:
    import cv2
    HAVE_CV2 = True
except ImportError:
    HAVE_CV2 = False

try:
    from pyzbar.pyzbar import decode
    HAVE_PYZBAR = True
except ImportError:
    HAVE_PYZBAR = False


class QrCodeExtractor(ProcessingModule):
    name = "qr_extractor"
    description = "Analyze files (via docement preview) to find QRcodes and decode them with two different libs."
    acts_on = ["png","jpg","jpeg", "pdf", "word", "html", "excel", "powerpoint"]
    triggered_by = "document_preview"
    config = [
        {
            "name": "skip_safe_file_review",
            "type": "bool",
            "default": False,
            "description": "Skip file review when no suspicious elements are found."
        }
    ]

# Check that libraries wer loaded correctly
    
    def initialize(self):
        if not HAVE_CV2:
            raise ModuleInitializationError(self, "Missing dependency: opencv2")
        if not HAVE_PYZBAR:
            raise ModuleInitializationError(self, "Missing dependency: pyzbar")
    
# For each, check if QRcode is found and extract potentiel URL
#   - TO-DO : include document preview for pdf to be able to read the qrcode
#               Or trigger the qrcode extractor after document preview
# possibly => mutualize Read image target
    # decode QRcode
    
    def extract_qr_code_by_opencv(img):
        image = cv2.imread(img, 0)
        try:
            detect = cv2.QRCodeDetector()
            value, points, straight_qrcode = detect.detectAndDecode(image)
            print(value)
            return value
        except:
            return

    def extract_qr_code_by_pyzbar(img):
        image = cv2.imread(img, 0)
        try:
            value = decode(image)
            print(value)
            return value
        except:
            return

    def each(self, target):
        self.results = {}
        
        # Get QRcode
        self.results[">PYZBAR"] = self.extract_qr_code_by_pyzbar(target)
        self.results[">OPENCV"] = self.extract_qr_code_by_opencv(target)	    
        self.add_ioc(results)
        #TO-DO add ioc for the url decoded only
        #if filetype == "url" and not target.startswith("http"):
        #    target = "http://{}".format(target)
        #if filetype == "url":
        #    self.add_ioc(target)
        return True

#TO-DO Include call to URL preview