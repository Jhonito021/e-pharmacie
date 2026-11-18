from time import perf_counter

from .models import JournalRequete


class JournalRequeteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        debut = perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            self._enregistrer(request, 500, debut)
            raise

        self._enregistrer(request, response.status_code, debut)
        return response

    @staticmethod
    def _enregistrer(request, statut, debut):
        user = getattr(request, 'user', None)
        JournalRequete.objects.create(
            utilisateur=user if getattr(user, 'is_authenticated', False) else None,
            methode=request.method[:10],
            chemin=request.path[:500],
            statut=statut,
            duree_ms=max(0, int((perf_counter() - debut) * 1000)),
        )
