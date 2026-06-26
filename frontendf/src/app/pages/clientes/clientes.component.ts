import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { firstValueFrom, Subscription } from 'rxjs';
import { ClienteService } from '../../services/cliente.service';
import { Cliente } from '../../models/cliente.model';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ClienteFormComponent } from './cliente-form/cliente-form.component';
import Swal from 'sweetalert2';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-clientes',
  standalone: true,
  imports: [CommonModule, FormsModule, MatTableModule, MatButtonModule, MatIconModule, MatCardModule, MatDialogModule],
  templateUrl: './clientes.component.html',
  styleUrl: './clientes.component.css'
})
export class ClientesComponent implements OnInit, OnDestroy {
  clientes: Cliente[] = [];
  displayedColumns = ['ruc', 'razon_social', 'nombre_comercial', 'size', 'acciones'];

  filtroTexto = '';
  private filterSub?: Subscription;
  filtroSize = '';

  sizeLabels: Record<string, string> = {
    PEQUENO: 'Pequeño',
    MEDIANO: 'Mediano',
    GRANDE: 'Grande',
    OFICINA: 'Oficina'
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
    private dialog: MatDialog,
    private globalFilter: GlobalFilterStateService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadClientes();
    this.filterSub = this.globalFilter.state$.subscribe(state => {
      if (!this.router.url.startsWith('/dashboard/clientes')) return;
      this.filtroTexto = state.query || '';
      this.loadClientes();
    });
  }

  ngOnDestroy(): void {
    this.filterSub?.unsubscribe();
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
      width: '1000px',
      maxWidth: '96vw',
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
      await firstValueFrom(this.clienteService.deleteCliente(cliente.id!));
      await Swal.fire({ icon: 'success', title: 'Eliminado', timer: 1200, showConfirmButton: false });
      this.loadClientes();
    } catch (err) {
      console.error('Error al eliminar:', err);
      Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar' });
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files && input.files[0];
    if (!file) return;
    this.clienteService.importClientes(file).subscribe({
      next: (res) => {
        const resumen = `Creados: ${res?.clientes_creados || 0}, Actualizados: ${res?.clientes_actualizados || 0}, Instalaciones creadas: ${res?.instalaciones_creadas || 0}, actualizadas: ${res?.instalaciones_actualizadas || 0}, Errores: ${res?.errores_total || 0}`;
        const errores = Array.isArray(res?.errores) ? res.errores : [];
        const erroresHtml = errores.length
          ? `<div style="text-align:left;max-height:220px;overflow:auto;margin-top:8px;">
                <strong>Errores:</strong>
                <ul style="margin:6px 0 0 18px;">${errores.map((e: string) => `<li>${e}</li>`).join('')}</ul>
             </div>`
          : '';
        Swal.fire({ icon: 'success', title: 'Importación', html: `${resumen}${erroresHtml}` });
        this.loadClientes();
      },
      error: (err) => {
        const msg = err?.error?.error || 'No se pudo importar';
        Swal.fire({ icon: 'error', title: 'Error', text: msg });
      }
    });
    // reset input value to allow re-upload same file
    input.value = '';
  }
}