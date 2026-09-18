import unittest
import numpy as np

from src.face_engine import FaceEngine


class FaceEnginePreprocessingTests(unittest.TestCase):
    def test_crop_preparation_uses_margin_and_square_shape(self):
        engine = FaceEngine(confidence_threshold=120.0, resize_factor=1)
        frame = np.zeros((240, 240, 3), dtype=np.uint8)

        crop = engine._crop_and_prepare_face(frame, 20, 30, 100, 100)

        self.assertIsNotNone(crop)
        self.assertEqual(crop.shape, (220, 220))


if __name__ == "__main__":
    unittest.main()
