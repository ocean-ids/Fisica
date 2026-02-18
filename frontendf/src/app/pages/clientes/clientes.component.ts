import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { ClienteService } from '../../services/cliente.service';
import { Cliente } from '../../models/cliente.model';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ClienteFormComponent } from './cliente-form/cliente-form.component';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-clientes',
  standalone: true,
  imports: [CommonModule, FormsModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule],
  templateUrl: './clientes.component.html',
  styleUrl: './clientes.component.css'
})
export class ClientesComponent implements OnInit {
  clientes: Cliente[] = [];
  displayedColumns = ['ruc', 'razon_social', 'nombre_comercial', 'size', 'acciones'];

  filtroTexto = '';
  filtroSize = '';

  sizeLabels: Record<string, string> = {
    PEQUENO: 'Pequeño',
    MEDIANO: 'Mediano',
    GRANDE: 'Grande'
  };

  get clientesFiltrados(): Cliente[] {
    const texto = this.filtroTexto.trim().toLowerCase();
    return this.clientes.filter(c => {
      const matchTexto = !texto ||
        (c.ruc || '').toLowerCase().includes(texto) ||
        (c.razon_social || '').toLowerCase().includes(texto) ||
        (c.nombre_comercial || '').toLowerCase().includes(texto);
      const matchSize = !this.filtroSize || c.size === this.filtroSize;
      return matchTexto && matchSize;
    });
  }

  constructor(
    private clienteService: ClienteService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadClientes();
  }

  loadClientes(): void {
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if (this.filtroSize) params.size = this.filtroSize;
    this.clienteService.getClientes(params).subscribe({
      next: data => this.clientes = data,
      error: err => console.error('Error al cargar clientes:', err)
    });
  }

  limpiarFiltros(): void {
    this.filtroTexto = '';
    this.filtroSize = '';
    this.loadClientes();
  }

  openDialog(cliente?: Cliente): void {
    const dialogRef = this.dialog.open(ClienteFormComponent, {
      width: '500px',
      data: cliente || {}
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (cliente?.id) {
          this.updateCliente(cliente.id, result);
        } else {
          this.createCliente(result);
        }
      }
    });
  }

  createCliente(cliente: Cliente): void {
    this.clienteService.createCliente(cliente).subscribe({
      next: () => {
        this.loadClientes();
        Swal.fire({ icon: 'success', title: 'Creado', timer: 1200, showConfirmButton: false });
      },
      error: (err: any) => {
        console.error('Error:', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo crear' });
      }
    });
  }

  updateCliente(id: number, cliente: Cliente): void {
    this.clienteService.updateCliente(id, cliente).subscribe({
      next: () => {
        this.loadClientes();
        Swal.fire({ icon: 'success', title: 'Actualizado', timer: 1200, showConfirmButton: false });
      },
      error: (err: any) => {
        console.error('Error:', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar' });
      }
    });
  }

  async confirmarEliminar(cliente: Cliente): Promise<void> {
    const res = await Swal.fire({
      title: '¿Eliminar cliente?',
      text: `Se eliminará ${cliente.nombre_comercial}`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!res.isConfirmed) return;

    try {
      await this.clienteService.deleteCliente(cliente.id!).toPromise();
      await Swal.fire({ icon: 'success', title: 'Eliminado', timer: 1200, showConfirmButton: false });
      this.loadClientes();
    } catch (err) {
      console.error('Error al eliminar:', err);
      Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar' });
    }
  }
}