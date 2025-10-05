import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ImagesPageTable } from './images-page-table';

describe('ImagesPageTable', () => {
  let component: ImagesPageTable;
  let fixture: ComponentFixture<ImagesPageTable>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ImagesPageTable]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ImagesPageTable);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
