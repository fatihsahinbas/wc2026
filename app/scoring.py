"""
Puanlama Mantığı
================
Kural (seçilen model):
  - Tahmin edilen sonuç (galibiyet/beraberlik) DOĞRUYSA → 3 puan
  - Yanlışsa → 0 puan

Bu modül, maç sonucu girildiğinde tüm ilgili tahminleri günceller.
"""
from . import db
from .models import Match, Prediction


CORRECT_OUTCOME_POINTS = 3
WRONG_OUTCOME_POINTS = 0


def calculate_points(predicted_outcome: str, actual_outcome: str) -> int:
    """
    İki outcome string karşılaştır, puan döndür.

    Args:
        predicted_outcome: 'home' | 'draw' | 'away'
        actual_outcome:    'home' | 'draw' | 'away'

    Returns:
        int: 3 (doğru) veya 0 (yanlış)
    """
    if predicted_outcome == actual_outcome:
        return CORRECT_OUTCOME_POINTS
    return WRONG_OUTCOME_POINTS


def recalculate_match_predictions(match: Match) -> dict:
    """
    Bir maçın tüm tahminlerini yeniden hesapla ve kaydet.

    Returns:
        {
            "match_id": int,
            "processed": int,   # güncellenen tahmin sayısı
            "correct": int,     # doğru tahmin sayısı
        }
    """
    if not match.is_finished or match.result_outcome is None:
        return {"match_id": match.id, "processed": 0, "correct": 0}

    actual = match.result_outcome
    predictions = match.predictions.all()

    processed = 0
    correct = 0

    for pred in predictions:
        pts = calculate_points(pred.predicted_outcome, actual)
        pred.points = pts
        if pts == CORRECT_OUTCOME_POINTS:
            correct += 1
        processed += 1

    db.session.commit()

    return {
        "match_id": match.id,
        "processed": processed,
        "correct": correct,
    }
