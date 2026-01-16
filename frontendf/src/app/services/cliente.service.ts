import { Injectable } from '@angular/core';
import { Observable, of, tap } from 'rxjs';
import { ApiService } from './api.service';
import { Cliente } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ClienteService {
  private cache: Cliente[] | null = null;

  constructor(private apiService: ApiService) { }

  getClientes(forceRefresh: boolean = false): Observable<Cliente[]> {
    if (!forceRefresh && this.cache) {
      return of(this.cache);
    }
    return this.apiService.get<Cliente[]>('/clientes/').pipe(
      tap(data => this.cache = data)
    );
  }

  getCliente(id: number): Observable<Cliente> {
    return this.apiService.get<Cliente>(`/clientes/${id}/`);
  } 

  createCliente(payload: Cliente): Observable<Cliente> {
    this.cache = null; // Invalidar caché
    return this.apiService.post<Cliente>('/crear-cliente/', payload);
  }

  updateCliente(id: number, payload: Cliente): Observable<Cliente>{
    this.cache = null; // Invalidar caché
    return this.apiService.put<Cliente>(`/actualizar-cliente/${id}/`, payload);
  }

  deleteCliente(id: number): Observable<any> {
    this.cache = null; // Invalidar caché
    return this.apiService.delete(`/eliminar-cliente/${id}/`);
  }
}