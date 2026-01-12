import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Puesto } from '../models';

@Injectable({
  providedIn: 'root'
})
export class PuestoService {

  constructor(private apiService: ApiService) { }

  getPuestos(): Observable<Puesto[]> {
    return this.apiService.get<Puesto[]>('/puestos/');
  }

  getPuesto(id: number): Observable<Puesto> {
    return this.apiService.get<Puesto>(`/puestos/${id}/`);
  }

  createPuesto(puesto: Puesto): Observable<Puesto> {
    return this.apiService.post<Puesto>('/puestos/', puesto);
  }

  updatePuesto(id: number, puesto: Puesto): Observable<Puesto> {
    return this.apiService.put<Puesto>(`/puestos/${id}/`, puesto);
  }

  deletePuesto(id: number): Observable<any> {
    return this.apiService.delete(`/puestos/${id}/`);
  }
}
