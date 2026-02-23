from rest_framework import generics, permissions, status
from rest_framework.response import Response
from ..models import PatronAsignacion
from ..serializers import PatronAsignacionSerializer

class PatronAsignacionListCreateView(generics.ListCreateAPIView):
    queryset = PatronAsignacion.objects.all()
    serializer_class = PatronAsignacionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
       
        print('DEBUG: POST /api/patrones/ data:', request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print('DEBUG: PatronAsignacion create errors:', serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

class PatronAsignacionRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PatronAsignacion.objects.all()
    serializer_class = PatronAsignacionSerializer
    permission_classes = [permissions.IsAuthenticated]