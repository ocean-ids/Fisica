import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { Cliente } from '../../models';
import { InstalacionService } from '../../services/instalacion.service';
import { ClienteService } from '../../services/cliente.service';
import { InstalacionFormComponent } from './instalacion-form/instalacion-form.component';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-instalaciones',
  standalone: true,
  imports: [CommonModule, FormsModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule],
  templateUrl: './instalaciones.component.html',
  styleUrl: './instalaciones.component.css'
})
export class InstalacionesComponent implements OnInit {
  instalaciones: any[] = [];
  clientes: Cliente[] = [];

  filtroTexto = '';

  constructor(
    private instalacionService: InstalacionService,
    private clienteService: ClienteService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.cargarInstalaciones();
    this.cargarClientes();
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
      provincia_id: data.provincia_id || data.provincia,
      canton_id: data.canton_id || data.canton,
      zona_id: data.zona_id || null
    };

    this.instalacionService.createInstalacion(payload).subscribe({
      next: () => {
        this.cargarInstalaciones();
        Swal.fire({ icon: 'success', title: 'Creada', timer: 1200, showConfirmButton: false });
      },
      error: (error: any) => {
        console.error('Error al crear instalación:', error);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo crear' });
      }
    });
  }

  actualizarInstalacion(id: number, data: any): void {
    const payload: any = {
      codigo: data.codigo || '',
      nombre: data.nombre || '',
      cliente: data.cliente_id,
      direccion: data.direccion || '',
      provincia_id: data.provincia_id || data.provincia,
      canton_id: data.canton_id || data.canton,
      zona_id: data.zona_id|| null,
    };

    this.instalacionService.updateInstalacion(id, payload).subscribe({
      next: () => {
        this.cargarInstalaciones();
        Swal.fire({ icon: 'success', title: 'Actualizada', timer: 1200, showConfirmButton: false });
      },
      error: (error: any) => {
        console.error('Error al actualizar instalación:', error);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar' });
      }
    });
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
      await this.instalacionService.deleteInstalacion(instalacion.id).toPromise();
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
