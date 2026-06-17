import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { PatronAsignacion } from '../../../models/asignacion.model';
import { PatronAsignacionService } from '../../../services/patron-asignacion.service';
import { MatDialog } from '@angular/material/dialog';
import { PatronFormComponent } from '../patron-form/patron-form.component';
// PatronFormComponent is opened via MatDialog; no template reference needed
@Component({
  selector: 'app-patrones-list',
  standalone: true,
  imports: [CommonModule, MatDialogModule],
  templateUrl: './patrones-list.component.html',
  styleUrl: './patrones-list.component.css'
})
export class PatronesListComponent {
  patrones: PatronAsignacion[] = [];
  loading = false;

  constructor(
    private patronService: PatronAsignacionService,
    private dialog: MatDialog
  ) {}
  abrirNuevoPatron(): void {
    const dialogRef = this.dialog.open(PatronFormComponent, {
      width: '400px',
      data: null
    });
    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.cargarPatrones();
      }
    });
  }

  abrirEditarPatron(patron: PatronAsignacion): void {
    const dialogRef = this.dialog.open(PatronFormComponent, {
      width: '400px',
      data: patron
    });
    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.cargarPatrones();
      }
    });
  }

  ngOnInit(): void {
    this.cargarPatrones();
  }

  cargarPatrones(): void {
    this.loading = true;
    this.patronService.obtenerPatrones().subscribe({
      next: (data) => {
        this.patrones = data;
        this.loading = false;
      },
      error: () => this.loading = false
    });
  }

  eliminarPatron(id: number): void {
    if (confirm('¿Estás seguro de eliminar este patrón?')) {
      this.patronService.eliminarPatron(id).subscribe(() => this.cargarPatrones());
    }
  }
}
