import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { CatalogoHorasEventual, HorasEventual, HorasEventualHistorialItem } from '../models/horas-eventual.model';

@Injectable({
  providedIn: 'root',
})
export class HorasEventualService {
  constructor(private api: ApiService) {}

  // Registros entre dos fechas (YYYY-MM-DD).
  listar(desde?: string, hasta?: string): Observable<HorasEventual[]> {
    const params: any = {};
    if (desde) { params.desde = desde; }
    if (hasta) { params.hasta = hasta; }
    return this.api.get<HorasEventual[]>('/horas-eventual/', params);
  }

  // Clientes, instalaciones, puestos y eventuales (con su banco) para los selectores.
  catalogo(): Observable<CatalogoHorasEventual> {
    return this.api.get<CatalogoHorasEventual>('/horas-eventual/catalogo/');
  }

  // Descargable Excel (mismas columnas que la tabla). params: fecha | desde/hasta, q.
  exportarExcel(params: any): Observable<Blob> {
    return this.api.getBlob('/horas-eventual/exportar-excel/', params);
  }

  crear(data: HorasEventual): Observable<HorasEventual> {
    return this.api.post<HorasEventual>('/horas-eventual/crear/', data);
  }

  actualizar(id: number, data: HorasEventual): Observable<HorasEventual> {
    return this.api.put<HorasEventual>(`/horas-eventual/${id}/`, data);
  }

  // Historial del registro (más reciente primero).
  historial(id: number): Observable<HorasEventualHistorialItem[]> {
    return this.api.get<HorasEventualHistorialItem[]>(`/horas-eventual/${id}/historial/`);
  }

  eliminar(id: number): Observable<any> {
    return this.api.delete(`/horas-eventual/${id}/eliminar/`);
  }
}
