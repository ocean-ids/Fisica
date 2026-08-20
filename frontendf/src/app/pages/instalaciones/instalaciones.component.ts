import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { firstValueFrom } from 'rxjs';
import { map, distinctUntilChanged, debounceTime, switchMap } from 'rxjs/operators';
import { Cliente } from '../../models';
import { InstalacionService } from '../../services/instalacion.service';
import { ClienteService } from '../../services/cliente.service';
import { InstalacionFormComponent } from './instalacion-form/instalacion-form.component';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';

import Swal from 'sweetalert2';

@Component({
  selector: 'app-instalaciones',
  standalone: true,
  imports: [CommonModule, FormsModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule],
  templateUrl: './instalaciones.component.html',
  styleUrl: './instalaciones.component.css'
})
export class InstalacionesComponent implements OnInit, OnDestroy {
  instalaciones: any[] = [];
  clientes: Cliente[] = [];

  filtroTexto = '';
  private filterSub?: Subscription;

  constructor(
    private instalacionService: InstalacionService,
    private clienteService: ClienteService,
    private dialog: MatDialog,
    private globalFilter: GlobalFilterStateService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.cargarClientes();
    // Buscador global: debounce + switchMap para no pisar respuestas viejas (evita el fallo intermitente).
    this.filterSub = this.globalFilter.state$.pipe(
      map(state => this.router.url.startsWith('/dashboard/instalaciones') ? (state?.query || '') : ''),
      distinctUntilChanged(),
      debounceTime(250),
      switchMap(q => {
        this.filtroTexto = q;
        const params: any = {};
        if (q.trim()) params.q = q.trim();
        return this.instalacionService.getInstalaciones(params);
      })
    ).subscribe({
      next: (data) => { this.instalaciones = data || []; },
      error: (err) => console.error('Error al cargar instalaciones:', err),
    });
  }

  ngOnDestroy(): void {
    this.filterSub?.unsubscribe();
  }

  cargarInstalaciones(): void {
    const params: any = {};
    if (this.filtroTexto.trim()) params.q = this.filtroTexto.trim();

    this.instalacionService.getInstalaciones(params).subscribe({
      next: (data) => {
        this.instalaciones = data;
      },
      error: (error) => console.error('Error al cargar instalaciones:', error)
    });
  }

  limpiarFiltros(): void {
    this.filtroTexto = '';
    this.cargarInstalaciones();
  }

  cargarClientes(): void {
    this.clienteService.getClientes().subscribe({
      next: (data) => {
        this.clientes = data;
      },
      error: (error: any) => console.error('Error al cargar clientes:', error)
    });
  }

  abrirModal(instalacion?: any): void {
    const dialogRef = this.dialog.open(InstalacionFormComponent, {
      width: '500px',
      autoFocus: false,
      data: { instalacion: instalacion || null, clientes: this.clientes }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (instalacion?.id) {
          this.actualizarInstalacion(instalacion.id, result);
        } else {
          this.crearInstalacion(result);
        }
      }
    });
  }

  crearInstalacion(data: any): void {
    const payload: any = {
      codigo: data.codigo || '',
      nombre: data.nombre || '',
      cliente: data.cliente_id,
      direccion: data.direccion || '',
      sector: data.sector || '',
      provincia_id: data.provincia_id || data.provincia,
      canton_id: data.canton_id || data.canton,
      zona_id: data.zona_id || null
    };

    this.instalacionService.createInstalacion(payload).subscribe({
      next: (resp: any) => {
        this.cargarInstalaciones();
        if (resp?.nominativo_aviso) {
          Swal.fire({ icon: 'info', title: 'Instalación creada', html: 'La instalación se creó correctamente.<br><br><b>Nominativo y Zona pendientes por asignación de Consola .</b>' });
        } else {
          Swal.fire({ icon: 'success', title: 'Creada', timer: 1200, showConfirmButton: false });
        }
      },
      error: (error: any) => {
        console.error('Error al crear instalación:', error);
        Swal.fire({ icon: 'error', title: 'No se pudo crear', text: error?.error?.error || 'No se pudo crear' });
      }
    });
  }

  actualizarInstalacion(id: number, data: any): void {
    const payload: any = {
      codigo: data.codigo || '',
      nombre: data.nombre || '',
      cliente: data.cliente_id,
      direccion: data.direccion || '',
      sector: data.sector || '',
      provincia_id: data.provincia_id || data.provincia,
      canton_id: data.canton_id || data.canton,
      zona_id: data.zona_id|| null,
    };

    this.instalacionService.updateInstalacion(id, payload).subscribe({
      next: (resp: any) => {
        this.cargarInstalaciones();
        if (resp?.nominativo_aviso) {
          Swal.fire({ icon: 'info', title: 'Instalación actualizada', html: 'La instalación se actualizó correctamente.<br><br><b>Nominativo y zona pendientes de asignación por Consola.</b>' });
        } else {
          Swal.fire({ icon: 'success', title: 'Actualizada', timer: 1200, showConfirmButton: false });
        }
      },
      error: (error: any) => {
        console.error('Error al actualizar instalación:', error);
        Swal.fire({ icon: 'error', title: 'No se pudo actualizar', text: error?.error?.error || 'No se pudo actualizar' });
      }
    });
  }

  async confirmarCerrar(instalacion: any): Promise<void> {
    const res = await Swal.fire({
      title: '¿Cerrar instalación?',
      html: `Se cerrará <b>${instalacion.nombre || ''}</b>.<br><br>` +
            'Se desactivarán sus puestos y asignaciones y se ' +
            'liberará su Nominativo por Zona.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, cerrar',
      cancelButtonText: 'Cancelar'
    });
    if (!res.isConfirmed) return;
    try {
      const r: any = await firstValueFrom(this.instalacionService.cerrarInstalacion(instalacion.id));
      await Swal.fire({
        icon: 'success', title: 'Instalación cerrada',
        text: `Puestos desactivados: ${r?.puestos_desactivados ?? 0} · Asignaciones: ${r?.asignaciones_desactivadas ?? 0}`,
      });
      this.cargarInstalaciones();
    } catch (error: any) {
      console.error('Error al cerrar instalación:', error);
      Swal.fire({ icon: 'error', title: 'No se pudo cerrar', text: error?.error?.error || 'No se pudo cerrar' });
    }
  }

  async confirmarReabrir(instalacion: any): Promise<void> {
    const res = await Swal.fire({
      title: '¿Reabrir instalación?',
      html: `Se reactivará <b>${instalacion.nombre || ''}</b> y sus puestos. ` ,
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Sí, reabrir',
      cancelButtonText: 'Cancelar'
    });
    if (!res.isConfirmed) return;
    try {
      const r: any = await firstValueFrom(this.instalacionService.reabrirInstalacion(instalacion.id));
      if (r?.nominativo_aviso) {
        await Swal.fire({ icon: 'info', title: 'Instalación reabierta', html: 'La instalación quedó activa nuevamente.<br><br><b>Nominativo y zona pendientes de asignación por Consola.</b>' });
      } else {
        await Swal.fire({ icon: 'success', title: 'Instalación reabierta', timer: 1400, showConfirmButton: false });
      }
      this.cargarInstalaciones();
    } catch (error: any) {
      console.error('Error al reabrir instalación:', error);
      Swal.fire({ icon: 'error', title: 'No se pudo reabrir', text: error?.error?.error || 'No se pudo reabrir' });
    }
  }

  async confirmarEliminar(instalacion: any): Promise<void> {
    const res = await Swal.fire({
      title: '¿Eliminar instalación?',
      text: `Se eliminará ${instalacion.nombre || ''}`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!res.isConfirmed) return;

    try {
      await firstValueFrom(this.instalacionService.deleteInstalacion(instalacion.id));
      await Swal.fire({ icon: 'success', title: 'Eliminada', timer: 1200, showConfirmButton: false });
      this.cargarInstalaciones();
    } catch (error) {
      console.error('Error al eliminar instalación:', error);
      Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar' });
    }
  }

  getNombreCliente(clienteId: number): string {
    const cliente = this.clientes.find(c => c.id === clienteId);
    return cliente ? cliente.nombre_comercial : 'N/A';
  }
}
